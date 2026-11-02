import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { createRequire } from "node:module";
import { arch, homedir, platform, tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { gunzipSync } from "node:zlib";

/** The embedded variant: libgascoigne called through koffi (see spec/native.md). */

const ABI = 1;

/** Configuration the library merges over its defaults and the user's file. */
export interface Settings {
  /** YAML laid over the defaults and the user's file. */
  config?: string;
  /** "dotted.path=value" assignments applied last. */
  set?: string[];
  only?: string[];
  disable?: string[];
  ignoreUserFile?: boolean;
  timeoutMs?: number;
}

/** What the library reads: the wire names of the options document. */
interface Wire {
  config?: string;
  set?: string[];
  only?: string[];
  disable?: string[];
  ignore_user_file?: boolean;
  timeout_ms?: number;
}

type Fn = {
  (...args: unknown[]): unknown;
  async: (...args: unknown[]) => void;
};

interface Koffi {
  load(path: string): { func(decl: string): Fn };
  decode(ptr: unknown, type: string, len?: number): string;
}

export class NativeError extends Error {}

/** `<os>-<arch>` as the bundle names its folders. */
function platformKey(): string {
  const names: Record<string, string> = { linux: "linux", darwin: "darwin", win32: "windows" };
  const os = names[platform()] ?? platform();
  return `${os}-${arch() === "x64" ? "amd64" : arch()}`;
}

/** Name of the npm package that carries this platform's library, as npm names os and cpu. */
function platformPackage(): string {
  return `@gascoigne-ai/sdk-native-${platform()}-${arch()}`;
}

/** This platform's entry of its @gascoigne-ai/sdk-native-<os>-<cpu> package, if installed. */
function bundledLibrary(): string | undefined {
  let root: string;
  try {
    root = dirname(createRequire(import.meta.url).resolve(`${platformPackage()}/package.json`));
  } catch {
    return undefined;
  }
  const dir = join(root, "lib", platformKey());
  if (!existsSync(dir)) return undefined;
  const entry = readdirSync(dir).find((f) => f.endsWith(".gz"));
  return entry ? join(dir, entry) : undefined;
}

/**
 * Unpacks a gzip-compressed library into the temp directory and returns the file to load. The
 * folder is named by the library's hash, so this is idempotent and an existing file is trusted
 * only when its content matches; the write goes through a temporary name and a rename.
 */
export function unpack(bundled: string): string {
  const data = gunzipSync(readFileSync(bundled));
  const sha = (b: Buffer) => createHash("sha256").update(b).digest("hex").slice(0, 16);
  const digest = sha(data);
  const folder = join(process.env.GASCOIGNE_LIB_DIR || tmpdir(), `gascoigne-native-${digest}`);
  const target = join(folder, bundled.replace(/^.*[\\/]/, "").replace(/\.gz$/, ""));
  if (existsSync(target) && sha(readFileSync(target)) === digest) return target;
  mkdirSync(folder, { recursive: true, mode: 0o700 });
  const partial = join(folder, `.${process.pid}.tmp`);
  writeFileSync(partial, data, { mode: 0o700 });
  renameSync(partial, target);
  return target;
}

/** Where an installed library may live: `$GASCOIGNE_LIB_PATH`, the CLI's dir, then the platform's
 * conventional places (spec/native.md). */
function systemDirs(): string[] {
  const dirs = (process.env.GASCOIGNE_LIB_PATH ?? "").split(delimiter).filter(Boolean);
  if (process.env.GASCOIGNE_BIN) dirs.push(dirname(process.env.GASCOIGNE_BIN));
  const home = homedir();
  if (platform() === "win32") {
    for (const v of ["LOCALAPPDATA", "ProgramFiles"]) {
      if (process.env[v]) dirs.push(join(process.env[v] as string, "gascoigne"));
    }
  } else if (platform() === "darwin") {
    dirs.push(join(home, ".local/lib"), "/usr/local/lib", "/opt/homebrew/lib");
  } else {
    const multiarch = `${arch() === "x64" ? "x86_64" : "aarch64"}-linux-gnu`;
    dirs.push(
      join(home, ".local/lib"),
      "/usr/local/lib",
      "/usr/lib",
      "/usr/lib64",
      join("/usr/lib", multiarch),
      "/opt/gascoigne/lib",
    );
  }
  return dirs;
}

const LIBRARY_NAMES = ["libgascoigne.so", "libgascoigne.dylib", "gascoigne.dll"];

/**
 * The library to load and where was looked, in order: `$GASCOIGNE_LIB`, the system directories,
 * then the @gascoigne-ai/sdk-native dependency unpacked to a temp directory.
 */
export function findLibrary(): { path?: string; looked: string[] } {
  const looked: string[] = [];
  const env = process.env.GASCOIGNE_LIB;
  if (env) {
    looked.push(`$GASCOIGNE_LIB=${env}`);
    return { path: existsSync(env) ? env : undefined, looked };
  }
  for (const dir of systemDirs()) {
    looked.push(dir);
    const found = LIBRARY_NAMES.map((n) => join(dir, n)).find((p) => existsSync(p));
    if (found) return { path: found, looked };
  }
  if (process.env.GASCOIGNE_UNPACK !== "off") {
    looked.push(`the ${platformPackage()} package`);
    const bundled = bundledLibrary();
    if (bundled) return { path: unpack(bundled), looked };
  }
  return { looked };
}

function wire(s: Settings): Wire {
  return {
    config: s.config,
    set: s.set,
    only: s.only,
    disable: s.disable,
    ignore_user_file: s.ignoreUserFile,
    timeout_ms: s.timeoutMs,
  };
}

/** An open engine in this process. */
export class Native {
  private constructor(
    private readonly koffi: Koffi,
    private readonly fns: Record<string, Fn>,
    private handle: bigint,
  ) {}

  /** Loads the library and starts an engine; throws NativeError when there is no library. */
  static open(settings: Settings, found = findLibrary()): Native {
    const path = found.path;
    if (!path) {
      throw new NativeError(
        `libgascoigne not found; looked in: ${found.looked.join(", ")}. ` +
          "Install it in one of those places or add the @gascoigne-ai/sdk-native package",
      );
    }
    let koffi: Koffi;
    try {
      // Resolved at run time, so koffi stays an optional dependency.
      koffi = createRequire(import.meta.url)("koffi") as Koffi;
    } catch {
      throw new NativeError("native mode needs the koffi package: npm install koffi");
    }
    const lib = koffi.load(path);
    const fns = {
      version: lib.func("int gascoigne_abi_version()"),
      open: lib.func("uint64_t gascoigne_open(const char *options, _Out_ void **err)"),
      optimize: lib.func("void *gascoigne_optimize(uint64_t h, const char *req, _Out_ void **err)"),
      raw: lib.func("void *gascoigne_raw(uint64_t h, const char *id, _Out_ void **err)"),
      close: lib.func("void gascoigne_close(uint64_t h)"),
      free: lib.func("void gascoigne_free(void *s)"),
    };
    if (fns.version() !== ABI) throw new NativeError(`${path} speaks another ABI than ${ABI}`);
    const n = new Native(koffi, fns, 0n);
    n.handle = n.openHandle(settings);
    return n;
  }

  private take(ptr: unknown): string {
    if (!ptr) return "";
    try {
      return this.koffi.decode(ptr, "char", -1);
    } finally {
      this.fns.free(ptr);
    }
  }

  private openHandle(settings: Settings): bigint {
    const err = [null];
    const h = BigInt(this.fns.open(JSON.stringify(wire(settings)), err) as number | bigint);
    if (!h) throw new NativeError(this.take(err[0]) || "open failed");
    return h;
  }

  private call(fn: "optimize" | "raw", arg: string): Promise<string> {
    const err = [null];
    return new Promise((resolve, reject) => {
      this.fns[fn].async(this.handle, arg, err, (e: Error | null, out: unknown) => {
        if (e) return reject(new NativeError(e.message));
        if (!out) return reject(new NativeError(this.take(err[0]) || `${fn} failed`));
        resolve(this.take(out));
      });
    });
  }

  optimize(requestJson: string): Promise<string> {
    return this.call("optimize", requestJson);
  }

  raw(id: string): Promise<string> {
    return this.call("raw", id);
  }

  close(): void {
    const h = this.handle;
    this.handle = 0n;
    if (h) this.fns.close(h);
  }
}
