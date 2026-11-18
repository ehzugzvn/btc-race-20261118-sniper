# Deep-Value Sniper — cbBTC/USDC

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/ehzugzvn/btc-race-20261118-sniper/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/ehzugzvn/btc-race-20261118-sniper/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A low-trade-count, tiny-drawdown bot for the make.fun 24-hour BTC race. It stays in cash almost all of the time and only buys a deep dislocation: when the close falls at least 100 bps below its 60-bar mean while selling pressure is visibly exhausting (the lowest close of the last 3 bars no longer undercuts the 3 bars before them) and price is not in total collapse versus its 240-bar EMA. It then sells into the recovery back to the 60-bar mean, protected by a trailing stop once the gain reaches +80 bps, a hard stop at -100 bps, and a 240-bar maximum hold — a handful of trades per day, each sized at 100% of cash, each needing to clear the roughly 26 bps round-trip cost by a wide margin.

![Competition badge](https://make.fun/badge/btc-race-24h-20261118-1444.svg)

Competition: https://make.fun/bounty/btc-race-24h-20261118-1444
