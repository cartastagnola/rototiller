import curses
import UIgraph as UIgraph

def init_colors(screen_state):  # UItiller.ScreenState
    screen_state.cursesColors = UIgraph.CustomColors(10)
    screen_state.colors["chia_green"] = UIgraph.addCustomColor(
        (47, 165, 67),
        screen_state.cursesColors)
    screen_state.colors["mini_block"] = UIgraph.addCustomColor(
        (100, 200, 100),
        screen_state.cursesColors)
    screen_state.colors["yellow_bee"] = UIgraph.addCustomColor(
        (255, 190, 0),
        screen_state.cursesColors)
    screen_state.colors["red"] = UIgraph.addCustomColor(
        (255, 0, 0),
        screen_state.cursesColors)
    screen_state.colors["orange_red"] = UIgraph.addCustomColor(
        (244, 43, 3),
        screen_state.cursesColors)
    screen_state.colors["orange_ee"] = UIgraph.addCustomColor(
        (254, 133, 13),
        screen_state.cursesColors)
    screen_state.colors["background"] = UIgraph.addCustomColor(
        (0, 10, 45),
        screen_state.cursesColors)
    screen_state.colors["background_header"] = UIgraph.addCustomColor(
        (20, 30, 65),
        screen_state.cursesColors)
    screen_state.colors["azure_up"] = UIgraph.addCustomColor(
        (80, 150, 210),
        screen_state.cursesColors)
    screen_state.colors["white_down"] = UIgraph.addCustomColor(
        (250, 245, 245),
        screen_state.cursesColors)
    screen_state.colors["tab_dark"] = UIgraph.addCustomColor(
        (0, 10, 45),
        screen_state.cursesColors)
    screen_state.colors["tab_soft"] = UIgraph.addCustomColor(
        (28, 36, 68),
        screen_state.cursesColors)
    screen_state.colors["tab_softer"] = UIgraph.addCustomColor(
        (38, 46, 78),
        screen_state.cursesColors)
    screen_state.colors["tab_selected"] = UIgraph.addCustomColor(
        (244, 43, 3),
        screen_state.cursesColors)
    screen_state.colors["bar_dark"] = UIgraph.addCustomColor(
        (20, 25, 50),
        screen_state.cursesColors)
    screen_state.colors["bar_soft"] = UIgraph.addCustomColor(
        (35, 40, 80),
        screen_state.cursesColors)
    screen_state.colors["orange_btc"] = UIgraph.addCustomColor(
        (247, 148, 19),
        screen_state.cursesColors)
    screen_state.colors["white"] = UIgraph.addCustomColor(
        (244, 245, 250),
        screen_state.cursesColors)
    screen_state.colors["gray"] = UIgraph.addCustomColor(
        (204, 205, 200),
        screen_state.cursesColors)
    screen_state.colors["dark_gray"] = UIgraph.addCustomColor(
        (104, 105, 100),
        screen_state.cursesColors)
    screen_state.colors["blue_dollar"] = UIgraph.addCustomColor(
        (46, 121, 204),
        screen_state.cursesColors)
    screen_state.colors["green_dollar"] = UIgraph.addCustomColor(
        (107, 128, 104),
        screen_state.cursesColors)

    screen_state.colorPairs["intro"] = UIgraph.addCustomColorTuple(
        (curses.COLOR_WHITE, screen_state.colors["chia_green"]),
        screen_state.cursesColors)
    screen_state.colorPairs["chia_wallet"] = UIgraph.addCustomColorTuple(
        (curses.COLOR_WHITE, screen_state.colors["chia_green"]),
        screen_state.cursesColors)
    screen_state.colorPairs["chia_wallet_bg"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["header"] = UIgraph.addCustomColorTuple(
        (curses.COLOR_BLACK, screen_state.colors["yellow_bee"]),
        screen_state.cursesColors)
    screen_state.colorPairs["header_W"] = UIgraph.addCustomColorTuple(
        (screen_state.colors['gray'], screen_state.colors["background_header"]),
        screen_state.cursesColors)
    screen_state.colorPairs["body"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["body_sel"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["background"], screen_state.colors["chia_green"]),
        screen_state.cursesColors)
    screen_state.colorPairs["footer"] = UIgraph.addCustomColorTuple(
        (curses.COLOR_BLACK, screen_state.colors["orange_red"]),
        screen_state.cursesColors)
    screen_state.colorPairs["nonode"] = UIgraph.addCustomColorTuple(
        (curses.COLOR_WHITE, screen_state.colors["orange_red"]),
        screen_state.cursesColors)
    screen_state.colorPairs["test"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["yellow_bee"], screen_state.colors["orange_red"]),
        screen_state.cursesColors)
    screen_state.colorPairs["test_red"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["orange_red"], screen_state.colors["orange_red"]),
        screen_state.cursesColors)
    screen_state.colorPairs["up"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["azure_up"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["down"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["white_down"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["tab_dark"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["tab_dark"]),
        screen_state.cursesColors)
    screen_state.colorPairs["tab_soft"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["tab_soft"]),
        screen_state.cursesColors)
    screen_state.colorPairs["tab_soft_bg"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["tab_soft"], screen_state.colors["tab_dark"]),
        screen_state.cursesColors)
    screen_state.colorPairs["tab_dark_bg"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["tab_dark"], screen_state.colors["tab_soft"]),
        screen_state.cursesColors)
    screen_state.colorPairs["tab_select"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["background"], screen_state.colors["chia_green"]),
        screen_state.cursesColors)
    screen_state.colorPairs["tab_selected"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["tab_selected"]),
        screen_state.cursesColors)
    screen_state.colorPairs["error"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["red"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["error_white"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["white"], screen_state.colors["red"]),
        screen_state.cursesColors)
    screen_state.colorPairs["bar_dark"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["bar_dark"]),
        screen_state.cursesColors)
    screen_state.colorPairs["bar_soft"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["bar_soft"]),
        screen_state.cursesColors)
    screen_state.colorPairs["xch"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["white"], screen_state.colors["chia_green"]),
        screen_state.cursesColors)
    screen_state.colorPairs["btc"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["white"], screen_state.colors["orange_btc"]),
        screen_state.cursesColors)
    screen_state.colorPairs["btc_inv"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["orange_btc"], screen_state.colors["white"]),
        screen_state.cursesColors)
    screen_state.colorPairs["btc_text"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["orange_btc"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["dollar"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["white"], screen_state.colors["green_dollar"]),
        screen_state.cursesColors)

    # win select
    screen_state.colorPairs["win_selected"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["yellow_bee"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["win_selected"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["gray"], screen_state.colors["background"]),
        screen_state.cursesColors)

    # use for selected block
    screen_state.colorPairs["win_selected_inactive"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["tab_softer"], screen_state.colors["gray"]),
        screen_state.cursesColors)
    screen_state.colorPairs["win_selected_inactive"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["tab_softer"], screen_state.colors["white_down"]),
        screen_state.cursesColors)

    screen_state.colorPairs["copy_banner"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["white"], screen_state.colors["tab_softer"]),
        screen_state.cursesColors)
    screen_state.colorPairs["block_band"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["block_band_mini"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["mini_block"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["block_band_synced"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["chia_green"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["block_band_syncing"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["orange_ee"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["block_band_no_sync"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["red"], screen_state.colors["background"]),
        screen_state.cursesColors)
    screen_state.colorPairs["scope_selected"] = UIgraph.addCustomColorTuple(
        (screen_state.colors["gray"], screen_state.colors["tab_dark"]),
        screen_state.cursesColors)

