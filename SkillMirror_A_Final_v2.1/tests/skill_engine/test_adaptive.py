from skill_engine.adaptive import choose_policy

def test_low_high(): assert choose_policy(40, .9)["mode"] == "teaching"
def test_high_low(): assert choose_policy(90, .4)["mode"] == "verification"
def test_high_high(): assert choose_policy(90, .9)["mode"] == "stretch"
def test_low_low(): assert choose_policy(40, .3)["mode"] == "diagnostic"
def test_unknown(): assert choose_policy(None, 0)["mode"] == "diagnostic"
