/* Battery driver for survey candidate 70 (PineForge native C API), items 2 and 4.
 * Rewritten 2026-09-26 (the item 2 source was removed from the scratchpad with its build); same command line
 * as the item 2 / item 4 adapters use:
 *   i2drv70 tf=.. tick=.. capital=.. fee_kind=.. fee_value=.. act=CALL:SIDE:TRIG:P1:P2:QTY ... cxl=CALL:ACTIDX ... -- ts_ms:o:h:l:c:v ...
 * SIDE b|s, TRIG 0 market / 1 limit (p1) / 2 stop (p1).  MAXA = 16 requests.  Synthetic input only. */
#define MAXA 16
#include <pineforge/pineforge.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

struct act { int call; char side; int trig; double p1, p2, qty; uint64_t inc; };
struct cxl { int call, idx; };
struct st { pf_strategy_t h; int calls, na, nc; struct act a[MAXA]; struct cxl c[MAXA]; };

static int on_bar(void* u, const pf_bar_t* b, const pf_native_decision_v1* at) {
    struct st* s = (struct st*)u; int i;
    (void)b; (void)at;
    s->calls++;
    for (i = 0; i < s->nc; i++) if (s->c[i].call == s->calls && s->c[i].idx >= 0 && s->c[i].idx < s->na)
        printf("CANCEL %d rc=%d\n", s->c[i].idx, strategy_native_cancel_v1(s->h, s->a[s->c[i].idx].inc));
    for (i = 0; i < s->na; i++) if (s->a[i].call == s->calls) {
        pf_native_request_v1 r; uint32_t rej = 0; int rc;
        memset(&r, 0, sizeof r);
        r.struct_size = sizeof r; r.version = PF_NATIVE_API_VERSION;
        r.intent = PF_NATIVE_INTENT_TRANSACT; r.intent_value = s->a[i].side == 'b' ? s->a[i].qty : -s->a[i].qty;
        if (s->a[i].trig == 1) { r.trigger = PF_NATIVE_TRIGGER_LIMIT; r.p1 = s->a[i].p1; }
        else if (s->a[i].trig == 2) { r.trigger = PF_NATIVE_TRIGGER_STOP; r.p1 = s->a[i].p1; }
        r.label = "battery";
        rc = strategy_native_submit_v1(s->h, &r, &s->a[i].inc, &rej);
        printf("SUBMIT %d rc=%d inc=%llu reject=%u\n", i, rc, (unsigned long long)s->a[i].inc, rej);
    }
    return 0;
}

static int on_applied(void* u, const pf_native_applied_v1* a, const pf_native_decision_v1* at) {
    struct st* s = (struct st*)u;
    printf("APPLIED call=%d eff=%lld inc=%llu price=%.17g opened=%.17g\n", s->calls, (long long)at->effective_time_ms,
           (unsigned long long)a->incarnation, a->resolved_price, a->opened_units);
    return 0;
}

int main(int argc, char** argv) {
    struct st s; pf_native_callbacks_v1 cb; pf_native_run_spec_v1 sp; pf_report_t rep;
    const char* tf = "1D"; double capital = 1000000, fee_value = 0, tick = 0.01; unsigned fee_kind = PF_NATIVE_FEE_PERCENT;
    pf_bar_t* bars = calloc((size_t)argc + 1, sizeof *bars); int n = 0, i, bar_args = 0, rc;
    memset(&s, 0, sizeof s);
    for (i = 1; i < argc; i++) {
        char* a = argv[i];
        if (!strcmp(a, "--")) { bar_args = 1; continue; }
        if (bar_args) {
            pf_bar_t* b = &bars[n++]; long long ts;
            sscanf(a, "%lld:%lf:%lf:%lf:%lf:%lf", &ts, &b->open, &b->high, &b->low, &b->close, &b->volume);
            b->timestamp = ts; continue;
        }
        if (!strncmp(a, "tf=", 3)) tf = a + 3;
        else if (!strncmp(a, "capital=", 8)) capital = atof(a + 8);
        else if (!strncmp(a, "tick=", 5)) tick = atof(a + 5);
        else if (!strncmp(a, "fee_kind=", 9)) fee_kind = (unsigned)atoi(a + 9);
        else if (!strncmp(a, "fee_value=", 10)) fee_value = atof(a + 10);
        else if (!strncmp(a, "act=", 4)) {
            struct act* x;
            if (s.na >= MAXA) { printf("ERROR too many requests (MAXA=%d)\n", MAXA); return 0; }
            x = &s.a[s.na++];
            if (sscanf(a + 4, "%d:%c:%d:%lf:%lf:%lf", &x->call, &x->side, &x->trig, &x->p1, &x->p2, &x->qty) != 6) { printf("ERROR bad act %s\n", a); return 0; }
        } else if (!strncmp(a, "cxl=", 4)) {
            if (s.nc >= MAXA) { printf("ERROR too many cancels\n"); return 0; }
            sscanf(a + 4, "%d:%d", &s.c[s.nc].call, &s.c[s.nc].idx); s.nc++;
        }
    }
    memset(&cb, 0, sizeof cb);
    cb.struct_size = sizeof cb; cb.version = PF_NATIVE_API_VERSION; cb.user = &s;
    cb.on_bar = on_bar; cb.on_applied = on_applied;
    s.h = strategy_native_host_create_v1(&cb);
    if (!s.h) { printf("ERROR create\n"); return 2; }
    memset(&sp, 0, sizeof sp);
    sp.struct_size = sizeof sp; sp.session_key = "battery"; sp.run_number = 1;
    sp.input_tf = tf; sp.script_tf = tf; sp.ticker = "X"; sp.tickerid = "TEST:X"; sp.type = "crypto";
    sp.currency = "JPY"; sp.basecurrency = "X"; sp.description = ""; sp.volumetype = "";
    sp.timezone = "UTC"; sp.session = "24x7"; sp.chart_timezone = "";
    sp.initial_capital = capital; sp.point_value = 1.0; sp.account_fx = 1.0; sp.price_tick = tick;
    sp.fee_kind = fee_kind; sp.fee_value = fee_value;
    sp.close_execution = PF_NATIVE_CLOSE_EXECUTION_NEXT_ELIGIBLE_POINT;
    sp.allowed_open_directions = PF_NATIVE_OPEN_DIRECTIONS_BOTH;
    if (strategy_configure_native_v1(s.h, &sp) != 0) { printf("ERROR configure %s\n", strategy_get_last_error(s.h)); return 0; }
    memset(&rep, 0, sizeof rep);
    rc = strategy_native_run_v1(s.h, bars, n, &rep);
    if (rc != PF_NATIVE_OK) printf("ERROR run rc=%d %s\n", rc, strategy_get_last_error(s.h));
    {
        pf_native_event_v1 ev[1024]; int k, m;
        for (k = 0; k < 1024; k++) { memset(&ev[k], 0, sizeof ev[k]); ev[k].struct_size = sizeof ev[k]; }
        m = strategy_native_events_v1(s.h, 0, ev, 1024);
        for (k = 0; k < m; k++)
            printf("EV kind=%u reason=%u inc=%llu price=%.17g resolved=%.17g opened=%.17g eff=%lld\n", ev[k].kind, ev[k].reason,
                   (unsigned long long)ev[k].incarnation, ev[k].price, ev[k].resolved_price, ev[k].opened_units, (long long)ev[k].effective_time_ms);
    }
    for (i = 0; i < rep.total_trades; i++)
        printf("TRADE qty=%.17g entry=%.17g entry_time=%lld commission=%.17g open_at_end=%d\n", rep.trades[i].qty, rep.trades[i].entry_price,
               (long long)rep.trades[i].entry_time, rep.trades[i].commission, rep.trades[i].open_at_end);
    strategy_native_report_free_v1(&rep);
    strategy_native_host_free(s.h);
    free(bars);
    return 0;
}
