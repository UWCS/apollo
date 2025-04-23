from cogs.commands.market import Market


def test_can_place_orders():
    m = Market("TEST")
    assert m.ask(102, 1, 1, 1) is None
    assert m.bid(101, 2, 3, 2) is None
    assert m.ask(102, 3, 4, 3) is None
    assert len(m.asks) == 2
    assert len(m.bids) == 1
    
    assert str(m) == """Market is: OPEN

📊 **TEST Order Book** 📊
```
Bid Orders      | Bid Volume      | Price      | Ask Volume      | Ask Orders
                |                 | 102.00     | 5               | 2
1               | 3               | 101.00     |                 |           
```
Last Trade: None"""

def test_single_match():
    m = Market("test")
    assert m.ask(101, 1, 1) is None
    assert (matched := m.bid(101, 2, 1)) is not None
    assert matched == "<@2> bought 1 from <@1> at 101"
    assert len(m.asks) == 0
    assert len(m.bids) == 0

def test_partial_match():
    m = Market("test")
    assert m.ask(102, 1, 100, 1) is None
    assert (o := m.bid(102, 2, 50, 2)) is not None
    assert o == "<@2> bought 50 from <@1> at 102"
    assert len(m.bids) == 0
    assert len(m.asks) == 1
    assert m.asks[0].qty == 50
    assert m.asks[0].order_time == 1

def test_multi_match():
    m = Market("test")
    assert m.ask(102, 1, 1, 1) is None
    assert m.ask(102, 2, 1, 2) is None
    assert m.ask(102, 3, 1, 4) is None
    assert m.bid(102, 4, 2, 5) == """<@4> bought 1 from <@1> at 102
<@4> bought 1 from <@2> at 102"""
    assert len(m.bids) == 0
    assert len(m.asks) == 1
    assert m.asks[0].user_id == 3
    assert len(m.trade_history[1]) == 1
    assert len(m.trade_history[2]) == 1
    assert 3 not in m.trade_history
    assert len(m.trade_history[4]) == 2

def test_turning():
    m = Market("test")
    assert m.ask(102, 1, 1, 1) is None
    assert m.bid(102, 2, 100, 2) == """<@2> bought 1 from <@1> at 102"""
    assert len(m.asks) == 0
    assert len(m.bids) == 1
    assert m.bids[0].qty == 99
    assert m.bids[0].order_time == 2

def test_multi_level_clear():
    m = Market("test")
    assert m.ask(100, 1, 1, 1) is None
    assert m.ask(101, 1, 1, 2) is None
    assert m.ask(102, 1, 1, 3) is None
    assert m.ask(103, 1, 100, 4) is None
    assert m.bid(103, 2, 10, 5) == """<@2> bought 1 from <@1> at 100
<@2> bought 1 from <@1> at 101
<@2> bought 1 from <@1> at 102
<@2> bought 7 from <@1> at 103"""
    assert len(m.bids) == 0
    assert len(m.asks) == 1
    assert m.asks[0].qty == 93
    assert m.asks[0].price == 103
    assert len(m.trade_history[1]) == 4
    assert len(m.trade_history[2]) == 4
