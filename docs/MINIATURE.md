# Hand check (synthetic ledger fixture, not the 252-session strategy)
Starting wealth 100 on 2025-01-30. A supplied prior-close instruction executes January 31: put half of **post-cost** wealth in equity at 100; fee rate .0005. Solve W + .0005 × .5W = 100, giving W=100/1.00025. Equity units=.5W/100; cash=.5W; inception cost=100−W.
February 3 equity price 110, no trade: wealth=1.05W; equity weight=.55/1.05=52.38095238%, proving drift. Zero fixture rates isolate accounting.
A February 3 after-close all-cash instruction executes February 4: sell .55W, pay .0005×.55W, ending wealth=1.05W−.000275W. Old units earn returns into February 4; new cash first earns February 4→5. Fixture values and independent reference are tested to absolute 1e-10 index points.

Strategy timeline: Friday 2025-01-31 is an XNYS month end. Its 252-return signal and 63-return covariance become known after close. Target executes Monday 2025-02-03 close, after old holdings earn January 31→February 3. New units earn February 3→4. Cash accrues three ACT/360 days over the weekend using a rate already available at January 31 close.
