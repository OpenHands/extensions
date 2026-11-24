extends Node2D

const CENTER := Vector2(202, 230)
const RADIUS := 123.0
const ICE := Color("96f2de")
const GOLD := Color("ffc475")
const INK := Color("233c50")
const MUTED := Color("93aaba")
const WHITE := Color("e6f4f4")
const TOTAL := 8

var angle := -PI / 2
var target := 0.0
var linked := 0
var charge := 3
var clock := 0.0
var flash := 0.0
var feedback := "Awaiting transmission"
var stars := PackedVector2Array()

func _ready() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 391
	for i in 78:
		stars.append(Vector2(rng.randf_range(12, 369), rng.randf_range(72, 393)))

func _process(dt: float) -> void:
	clock += dt
	flash = maxf(0.0, flash - dt)
	if linked < TOTAL and charge > 0:
		angle = wrapf(angle + dt * (1.2 + linked * 0.17), -PI, PI)
	queue_redraw()

func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	var click := event as InputEventMouseButton
	if (key and key.pressed and not key.echo and key.keycode in [KEY_SPACE, KEY_ENTER]) or (click and click.pressed and click.button_index == MOUSE_BUTTON_LEFT):
		transmit()

func transmit() -> void:
	if linked == TOTAL or charge == 0:
		angle = -PI / 2
		target = 0.0
		linked = 0
		charge = 3
		feedback = "Awaiting transmission"
		flash = 0.0
		return
	flash = 0.42
	if absf(angle_difference(angle, target)) <= gate_width():
		linked += 1
		target = wrapf(target + 1.9 + 0.75 * sin(linked * 1.7), -PI, PI)
		feedback = "Carrier locked"
	else:
		charge -= 1
		feedback = "Missed the window"

func gate_width() -> float:
	return 0.37 - linked * 0.018

func label(pos: Vector2, text: String, size: int, tint: Color) -> void:
	draw_string(ThemeDB.fallback_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, tint)

func orbit(a: float, r: float) -> Vector2:
	return CENTER + Vector2.from_angle(a) * r

func _draw() -> void:
	for i in stars.size():
		draw_circle(stars[i], 0.6 + (i % 3) * 0.35, Color(MUTED, 0.36 + 0.2 * sin(clock + i)))
	label(Vector2(24, 34), "FAR FIELD   /   ORBITAL SYSTEMS", 14, ICE)
	label(Vector2(563, 34), "STATION     07—B", 14, MUTED)
	draw_line(Vector2(24, 52), Vector2(696, 52), INK)
	for i in 72:
		var a := TAU * i / 72.0
		draw_line(orbit(a, 142), orbit(a, 148 if i % 6 == 0 else 144), MUTED if i % 6 == 0 else INK, 1, true)
	draw_arc(CENTER, RADIUS, 0, TAU, 150, INK, 2, true)
	draw_circle(CENTER, 65, Color("102434"), true, -1, true)
	# Latitude rings and a tilted dust belt give the relay planet its silhouette.
	for i in 6:
		var y := -48.0 + i * 18
		var half := sqrt(65 * 65 - y * y)
		draw_line(CENTER + Vector2(-half, y), CENTER + Vector2(half, y), INK, 1, true)
	var belt := PackedVector2Array()
	for i in 97:
		var t := TAU * i / 96
		belt.append(CENTER + Vector2(92 * cos(t), 19 * sin(t)).rotated(-0.35))
	draw_polyline(belt, Color("48667a"), 2, true)
	draw_arc(CENTER, RADIUS, target-gate_width(), target+gate_width(), 32, GOLD, 9, true)
	for edge in [-1, 1]:
		var a := target + float(edge) * gate_width()
		draw_line(orbit(a, RADIUS-9), orbit(a, RADIUS+9), GOLD, 2, true)
	for i in 10:
		draw_circle(orbit(angle-i*0.033, RADIUS), 6.5-i*0.5, Color(ICE, 1-i*0.099), true, -1, true)
	draw_circle(orbit(angle, RADIUS), 3, WHITE)
	if flash > 0:
		draw_arc(orbit(angle, RADIUS), 7 + (0.42-flash)*62, 0, TAU, 36, Color(ICE if feedback == "Carrier locked" else GOLD, flash*2), 2, true)
	var x := 397
	label(Vector2(x, 98), "TELEMETRY   /   %02d" % (mini(linked + 1, TOTAL)), 14, GOLD)
	label(Vector2(x, 151), "Periapsis", 49, WHITE)
	var ended := linked == TOTAL or charge == 0
	label(Vector2(x, 191), "Network online." if linked == TOTAL else ("Signal lost." if ended else "Send a pulse as the satellite"), 18, WHITE)
	label(Vector2(x, 216), "Tap to fly again." if ended else "crosses the amber arc.", 18, MUTED)
	label(Vector2(x, 270), "LINKS    %02d / 08" % linked, 14, ICE)
	for i in TOTAL:
		draw_rect(Rect2(x+i*32, 281, 27, 7), ICE if i < linked else INK)
	label(Vector2(x, 332), "RESERVE", 14, MUTED)
	for i in 3:
		draw_circle(Vector2(x+93+i*18, 327), 4.5, GOLD if i < charge else INK, true, -1, true)
	draw_line(Vector2(24, 397), Vector2(696, 397), INK)
	label(Vector2(24, 427), "SPACE  /  TAP     •     " + ("Restart" if ended else "Transmit"), 15, WHITE)
	label(Vector2(x, 427), feedback, 15, GOLD if feedback == "Missed the window" else ICE)
