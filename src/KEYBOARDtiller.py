import curses
import src.TYPEStiller as TYPE


# move this part in a funciton to process input, and then run this inside the
# scope execution. Easier to change a scope behaviuor if needed.
# EG: func_input_proces_visual, func_input_process_insert
# and call it when the scope is active
def processing(stdscr, screen_state: TYPE.ScreenState, keyboard_state: TYPE.KeyboardState,
               active_scope: TYPE.Scope):

    exit_roto = False

    while True:
        key = stdscr.getch()
        if key == -1:
            break

        if key >= 0:
            keyboard_state.key = chr(key)

        if key == curses.KEY_ENTER or key == 10 or key == 13:
            keyboard_state.enter = True
            return
        if key == 27:
            keyboard_state.esc = True
            return
        if key == 6:  # ctrl-f
            CONF.FIGLET = not CONF.FIGLET

        if key == ord('q'):
            exit_roto = True

        match active_scope.mode:
            case TYPE.ScopeMode.INSERT:
                match key:
                    case curses.KEY_BACKSPACE:
                        idx = active_scope.data['cursor'] - 1
                        if idx < 0:
                            pass
                        else:
                            s = active_scope.data['prompt']
                            active_scope.data['prompt'] = s[:idx] + s[idx + 1:]
                            active_scope.data['cursor'] -= 1
                    case curses.KEY_DC:
                        idx = active_scope.data['cursor']
                        s = active_scope.data['prompt']
                        if idx > len(s):
                            pass
                        else:
                            active_scope.data['prompt'] = s[:idx] + s[idx + 1:]
                    case curses.KEY_LEFT:
                        active_scope.data['cursor'] -= 1
                    case curses.KEY_RIGHT:
                        active_scope.data['cursor'] += 1
                    case curses.KEY_UP:
                        pass
                    case curses.KEY_DOWN:
                        pass
                    case 22:  # ctrl-v
                        keyboard_state.paste = True
                    case _:
                        idx = active_scope.data['cursor']
                        s = active_scope.data['prompt']
                        active_scope.data['prompt'] = s[:idx] + chr(key) + s[idx:]
                        active_scope.data['cursor'] += 1

            case TYPE.ScopeMode.VISUAL:

                if key == ord('j') or key == curses.KEY_DOWN:
                    keyboard_state.moveDown = True
                if key == ord('k') or key == curses.KEY_UP:
                    keyboard_state.moveUp = True
                if key == ord('h') or key == curses.KEY_LEFT:
                    keyboard_state.moveLeft = True
                if key == ord('l') or key == curses.KEY_RIGHT:
                    keyboard_state.moveRight = True
                if key == curses.KEY_MOUSE:
                    keyboard_state.mouse = True
                if key == ord('y'):
                    keyboard_state.yank = True
                if key == ord('0') or key == curses.KEY_HOME:
                    keyboard_state.home = True
                if key == 22 or key == ord('p'):  # ctrl-v
                    keyboard_state.paste = True

    return exit_roto


def execution(screen_state: TYPE.ScreenState, keyboard_state: TYPE.KeyboardState,
              active_scope: TYPE.Scope):

    # TODO: move keyboard execution to the active screen
    ## and re-think the scope activation/execution
    ## now: exec_child when there are child
    ## or exec_own when there are no child
    if keyboard_state.enter is True:
        active_scope.exec_child(*screen_state.scope_exec_args)
        return
    if keyboard_state.esc is True:
        # exec_esc is not a method but a property
        # should i create a method to call it?
        active_scope.exec_esc(active_scope, *screen_state.scope_exec_args)
        return

    if keyboard_state.moveUp:
        active_scope.cursor -= 1
        screen_state.selection = -1
    if keyboard_state.moveDown:
        active_scope.cursor += 1
        screen_state.selection = 1
    # flipped for block_band
    if keyboard_state.moveLeft:
        active_scope.cursor_x += 1
    if keyboard_state.moveRight:
        active_scope.cursor_x -= 1

