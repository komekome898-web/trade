# Hand derivation — return-kind (log vs simple) known-answer case

Planted EXACTLY 5.0bps of simple overnight return: open(t+1) = close(t) * (1 + 0.0005).

close(t) = 1000.0, open(t+1) = 1000.5

hand r_simple = open(t+1)/close(t) - 1 = 0.0005000000 (5.000000bps)
hand r_log    = ln(open(t+1)/close(t)) = 0.0004998750
function r_simple = 0.0005000000  (matches hand: True)
function r_log    = 0.0004998750  (matches hand: True)
simple recovers planted 5.0bps exactly: True

r_simple - r_log = 0.000000124958
first-order approx r_simple**2/2 = 0.000000125000
relative error = 0.000333 (first_order_matches <1%: True)
