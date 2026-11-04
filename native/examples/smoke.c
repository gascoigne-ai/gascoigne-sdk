#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libgascoigne.h"

/* Opens an engine, optimizes a repetitive log, prints the response. */
int main(void) {
	char *err = NULL;
	if (gascoigne_abi_version() != 2) return 2;
	unsigned long long h = gascoigne_open("{\"ignore_user_file\":true,\"config\":\"extensions:\\n  ledger:\\n    path: /tmp/gascoigne-smoke.db\\n\"}", &err);
	if (!h) { fprintf(stderr, "open: %s\n", err); return 1; }
	char *req = malloc(400 * 64 + 64);
	strcpy(req, "{\"text\":\"");
	char *p = req + strlen(req);
	for (size_t i = 0; i < 400; i++) p += sprintf(p, "INFO request served path=/api/items status=200 ms=12\\n");
	strcpy(p, "\",\"tool\":\"bash\"}");
	char *out = gascoigne_optimize(h, req, &err);
	if (!out) { fprintf(stderr, "optimize: %s\n", err); return 1; }
	puts(out);
	gascoigne_free(out);
	/* Counted by the ledger: one run. */
	char *stats = gascoigne_stats(h, "{\"by\":\"agent\"}", &err);
	if (!stats) { fprintf(stderr, "stats: %s\n", err); return 1; }
	puts(stats);
	gascoigne_free(stats); gascoigne_free(err); free(req);
	gascoigne_close(h);
	return 0;
}
