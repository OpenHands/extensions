extends SceneTree
func _initialize():
    var game = load("res://relay.tscn").instantiate()
    for i in 8:
        game.angle = game.target
        game.transmit()
    assert(game.linked == 8)
    game.transmit()
    assert(game.linked == 0 and game.charge == 3)
    for i in 3:
        game.transmit()
    assert(game.charge == 0)
    game.transmit()
    assert(game.charge == 3)
    game.free()
    print("Win, loss, restart OK")
    quit()
