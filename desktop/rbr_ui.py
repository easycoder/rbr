#   rbr_ui.py — AllSpeak plugin for the RBR desktop app.
#
# Registers the RBR-specific variable types (rbrwin, topbar, profilesbar,
# room, sheet, button) with the Python graphics runtime, plus the commands
# the app script uses: create, add, attach, set, show, hide, clear and
# on click.
#
# These types are specific to the Room-By-Room UI, so they live in this
# plugin rather than the AllSpeak core pack (see
# doc/PROPOSAL-allspeak-rounded-rectangle.md for the core-pack discussion).

import json

from allspeak import Handler, RuntimeError
from allspeak.as_classes import ECValue
from allspeak.as_program import flush

from rbrwidgets import (
    ECRBRButton, ECRBRCalendarSheet, ECRBRProfileSheet, ECRBRProfiles, ECRBRRoom, ECRBRRoomsSheet, ECRBRSchedSheet, ECRBRSheet, ECRBRTopBar,
    ECRBRWin, CalendarSheet, ProfileBar, ProfileSheet, RBRButton as WidgetButton, RBRMainWindow, RoomCard, RoomsSheet, ScheduleSheet,
    Sheet, TopBar,
)


class ReplaceFirstReceiver:
    """Wrap a TextReceiver so the first typed character replaces any
    pre-filled content. The keypad only appends (getContent() + char), so a
    pre-filled field would otherwise become 'oldtext' + newtext. Backspace,
    setContent (used by the keyboard's cancel/restore) and getContent pass
    through untouched."""

    def __init__(self, receiver):
        self._r = receiver
        self._first = True

    def addCharacter(self, char):
        if self._first and self._r.getContent():
            self._r.setContent('')
        self._first = False
        self._r.addCharacter(char)

    def backspace(self):
        self._first = False
        self._r.backspace()

    def setContent(self, text):
        self._first = False
        self._r.setContent(text)

    def getContent(self):
        return self._r.getContent()


class RBR_UI(Handler):

    def __init__(self, compiler):
        Handler.__init__(self, compiler)

    def getName(self):
        return 'rbr_ui'

    # Optional domain hooks — value compilation calls these on every domain
    def modifyValue(self, value):
        return value

    def compileValue(self):
        return None

    ###########################################################################
    # Variable type declarations

    def k_rbrwin(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRWin')

    def r_rbrwin(self, command):
        return self.nextPC()

    def k_topbar(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRTopBar')

    def r_topbar(self, command):
        return self.nextPC()

    def k_profilesbar(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRProfiles')

    def r_profilesbar(self, command):
        return self.nextPC()

    def k_room(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRRoom')

    def r_room(self, command):
        return self.nextPC()

    def k_sheet(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRSheet')

    def r_sheet(self, command):
        return self.nextPC()

    def k_schedsheet(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRSchedSheet')

    def r_schedsheet(self, command):
        return self.nextPC()

    def k_profilesheet(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRProfileSheet')

    def r_profilesheet(self, command):
        return self.nextPC()

    def k_roomsheet(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRRoomsSheet')

    def r_roomsheet(self, command):
        return self.nextPC()

    def k_calendarsheet(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRCalendarSheet')

    def r_calendarsheet(self, command):
        return self.nextPC()

    def k_button(self, command):
        self.compiler.addValueType()
        return self.compileVariable(command, 'ECRBRButton')

    def r_button(self, command):
        return self.nextPC()

    ###########################################################################
    # create {symbol} [title X] [size W H] [spec X] [index N]

    def k_create(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            cls = self.getObject(record)
            if isinstance(cls, (ECRBRRoom, ECRBRWin, ECRBRTopBar, ECRBRProfiles, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRRoomsSheet, ECRBRCalendarSheet, ECRBRButton)):
                command['name'] = record['name']
                command['object'] = cls
                while True:
                    token = self.peek()
                    if token == 'title':
                        self.nextToken()
                        command['title'] = self.nextValue()
                    elif token == 'size':
                        self.nextToken()
                        command['width'] = self.nextValue()
                        command['height'] = self.nextValue()
                    elif token == 'spec':
                        self.nextToken()
                        command['spec'] = self.nextValue()
                    elif token == 'index':
                        self.nextToken()
                        command['index'] = self.nextValue()
                    else:
                        break
                self.add(command)
                return True
        return False

    def r_create(self, command):
        record = self.getVariable(command['name'])
        cls = self.getObject(record)
        widget = None
        if isinstance(cls, ECRBRWin):
            widget = RBRMainWindow()
            if 'title' in command:
                widget.setWindowTitle(self.textify(command['title']))
            # Orient the window to the screen: on a portrait device (height
            # > width) fill the whole screen; on a landscape device draw a
            # 9:16 portrait-shaped window (simulating a typical portrait
            # tablet/phone). The size is FIXED so adding widgets (e.g. the
            # calling-for-heat pill) never widens the window.
            sw = getattr(self.program, 'screenWidth', None)
            sh = getattr(self.program, 'screenHeight', None)
            if sw and sh and sh > sw:
                widget.setFixedSize(sw, sh)
                widget.maximizeOnShow = True
            elif sw and sh:
                widget.setFixedSize(round(sh * 9 / 16), sh)
                widget.maximizeOnShow = False
            else:
                widget.setFixedSize(430, 800)
                widget.maximizeOnShow = False
        elif isinstance(cls, ECRBRTopBar):
            widget = TopBar()
        elif isinstance(cls, ECRBRProfiles):
            widget = ProfileBar()
        elif isinstance(cls, ECRBRRoom):
            spec = self.textify(command['spec']) if 'spec' in command else '{}'
            try:
                spec_dict = json.loads(spec) if isinstance(spec, str) else spec
            except (json.JSONDecodeError, TypeError):
                spec_dict = {}
            index = 0
            if 'index' in command:
                try:
                    index = int(self.textify(command['index']))
                except (TypeError, ValueError):
                    index = 0
            widget = RoomCard(spec_dict, index)
        elif isinstance(cls, ECRBRSheet):
            widget = Sheet()
            if 'title' in command:
                widget.setTitle(self.textify(command['title']))
        elif isinstance(cls, ECRBRSchedSheet):
            widget = ScheduleSheet()
            if 'title' in command:
                widget.setTitle(self.textify(command['title']))
        elif isinstance(cls, ECRBRProfileSheet):
            widget = ProfileSheet()
            if 'title' in command:
                widget.setTitle(self.textify(command['title']))
        elif isinstance(cls, ECRBRRoomsSheet):
            widget = RoomsSheet()
            if 'title' in command:
                widget.setTitle(self.textify(command['title']))
        elif isinstance(cls, ECRBRCalendarSheet):
            widget = CalendarSheet()
            if 'title' in command:
                widget.setTitle(self.textify(command['title']))
        elif isinstance(cls, ECRBRButton):
            text = self.textify(command['title']) if 'title' in command else ''
            widget = WidgetButton(text)
        if widget is not None:
            cls.setWidget(widget)
        return self.nextPC()

    ###########################################################################
    # add {room} to {rbrwin} | add {sheet} to {rbrwin}

    def k_add(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, (ECRBRRoom, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRRoomsSheet, ECRBRCalendarSheet)):
                command['item'] = record['name']
                self.skip('to')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if self.isObjectType(record, ECRBRWin):
                        command['window'] = record['name']
                        self.add(command)
                        return True
        return False

    def r_add(self, command):
        item_rec = self.getVariable(command['item'])
        item = self.getInnerObject(item_rec)
        window_rec = self.getVariable(command['window'])
        window = self.getInnerObject(window_rec)
        if isinstance(item, RoomCard):
            window.addRoomCard(item)
            # Wire the click handler set by `on click Room` to THIS card.
            # Note: we do NOT call obj.setIndex(index) — the shared `room`
            # variable stores a single value, so setting its index to the
            # card's index (1..n-1) makes getValue() crash with
            # "list index out of range". The clicked card's index travels
            # in its pending dict instead (getPending adds 'index').
            obj = self.getObject(item_rec)
            pc = getattr(obj, 'clickPC', None)
            if pc is not None:
                def handler(*args, **kwargs):
                    # Remember which card was clicked so `get pending of
                    # Room` reads THIS card's pending, not the last one
                    # rendered (the shared `room` variable holds the last
                    # card only). The index travels in the pending dict.
                    obj.lastClicked = item
                    self.run(pc)
                    flush()

                item.setClickCallback(handler)
        elif isinstance(item, Sheet):
            window.addSheet(item)
        return self.nextPC()

    ###########################################################################
    # addrow {label} [sub {sub}] [id {id}] to {sheet} — a menu row.
    # (Named addrow because core's `add` raises on a bare-word value.)

    def k_addrow(self, command):
        command['type'] = 'row'
        command['label'] = self.nextValue()
        while True:
            token = self.peek()
            if token == 'sub':
                self.nextToken()
                command['sub'] = self.nextValue()
            elif token == 'id':
                self.nextToken()
                command['id'] = self.nextValue()
            elif token == 'to':
                self.nextToken()
                break
            else:
                break
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, ECRBRSheet):
                command['sheet'] = record['name']
                self.add(command)
                return True
        return False

    def r_addrow(self, command):
        sheet_rec = self.getVariable(command['sheet'])
        sheet = self.getInnerObject(sheet_rec)
        label = self.textify(command['label'])
        sub = self.textify(command['sub']) if 'sub' in command else ''
        row_id = self.textify(command['id']) if 'id' in command else label
        sheet.addRow(label, sub, row_id)
        return self.nextPC()

    ###########################################################################
    # addinput {label} [initial {value}] to {sheet} — a text-input row for
    # the name/request/add dialogs.

    def k_addinput(self, command):
        command['type'] = 'input'
        command['label'] = self.nextValue()
        if self.peek() == 'initial':
            self.nextToken()
            command['initial'] = self.nextValue()
        self.skip('to')
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, ECRBRSheet):
                command['sheet'] = record['name']
                self.add(command)
                return True
        return False

    def r_addinput(self, command):
        sheet_rec = self.getVariable(command['sheet'])
        sheet = self.getInnerObject(sheet_rec)
        label = self.textify(command['label'])
        initial = self.textify(command['initial']) if 'initial' in command else ''
        sheet.addInput(label, initial)
        return self.nextPC()

    ###########################################################################
    # get pending of {room} into {dict}
    # get name of {room} into {var}
    # get input of {sheet} into {var}
    # get row of {sheet} into {var}
    # get index of {profilesbar} into {var}

    def k_get(self, command):
        token = self.peek()
        if token in ('pending', 'name', 'input', 'row', 'index'):
            self.nextToken()
            command['type'] = token
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if self.isObjectType(record, (ECRBRRoom, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRRoomsSheet, ECRBRCalendarSheet, ECRBRProfiles)):
                    command['target'] = record['name']
                    self.skip('into')
                    if self.nextIsSymbol():
                        command['destination'] = self.getSymbolRecord()['name']
                        self.add(command)
                        return True
        return False

    def r_get(self, command):
        target_rec = self.getVariable(command['target'])
        obj = target_rec['object']
        dest = self.getVariable(command['destination'])
        ctype = command['type']
        if ctype == 'index':
            # A profile-pill click stores the chosen index on the wrapper's
            # `lastIndex` — the EC `index`/`values` are NOT reused for it
            # (index doubles as the element cursor, so setIndex would make
            # getInnerObject read values[idx] out of range — values holds
            # exactly one widget).
            index = getattr(obj, 'lastIndex', None) or 0
            self.putSymbolValue(dest, ECValue(type=int, content=index))
            return self.nextPC()
        target = self.getInnerObject(target_rec)
        if ctype == 'pending':
            # Read the pending from the card that was actually clicked
            # (lastClicked), falling back to the widget itself.
            card = getattr(obj, 'lastClicked', None) or target
            pending = card.getPending() if hasattr(card, 'getPending') else None
            content = pending if isinstance(pending, dict) else {}
            self.putSymbolValue(dest, ECValue(type='dict', content=content))
        elif ctype == 'name':
            name = target.spec.get('name', '') if hasattr(target, 'spec') else ''
            self.putSymbolValue(dest, ECValue(type=str, content=name))
        elif ctype == 'input':
            value = target.getInput() if hasattr(target, 'getInput') else ''
            self.putSymbolValue(dest, ECValue(type=str, content=value))
        elif ctype == 'row':
            value = target.getPendingRow() if hasattr(target, 'getPendingRow') else ''
            self.putSymbolValue(dest, ECValue(type=str, content=value))
        return self.nextPC()

    ###########################################################################
    # attach {topbar|profilesbar} to {rbrwin}

    def k_attach(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, (ECRBRTopBar, ECRBRProfiles)):
                command['item'] = record['name']
                self.skip('to')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    if self.isObjectType(record, ECRBRWin):
                        command['window'] = record['name']
                        self.add(command)
                        return True
        return False

    def r_attach(self, command):
        item_rec = self.getVariable(command['item'])
        item = self.getInnerObject(item_rec)
        window_rec = self.getVariable(command['window'])
        window = self.getInnerObject(window_rec)
        if isinstance(item, TopBar):
            window.setTopBar(item)
        elif isinstance(item, ProfileBar):
            window.setProfileBar(item)
        return self.nextPC()

    ###########################################################################
    # set system name of {rbrwin} to {value}
    # set heart of {rbrwin} [to {value}]
    # set calling of {rbrwin} to {value}
    # set profiles of {profilesbar} to {value} [selected {value}]
    # set title of {sheet} to {value}
    # set text of {topbar|button} to {value}
    # set spec of {room} to {value}
    # set temp of {room} to {value}

    def k_set(self, command):
        token = self.peek()
        if token in ('system', 'heart', 'request', 'calling', 'input', 'profiles', 'profile', 'periods', 'rooms', 'days', 'calendar', 'title', 'text', 'spec', 'temp'):
            self.nextToken()
            command['type'] = token
            if token == 'system':
                self.skip('name')
            self.skip('of')
            if not self.nextIsSymbol():
                return False
            record = self.getSymbolRecord()
            if self.isObjectType(record, (ECRBRWin, ECRBRTopBar, ECRBRProfiles, ECRBRRoom, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRRoomsSheet, ECRBRCalendarSheet, ECRBRButton)):
                command['target'] = record['name']
                self.skip('to')
                command['value'] = self.nextValue()
                if token == 'profiles' and self.peek() == 'selected':
                    self.nextToken()
                    command['selected'] = self.nextValue()
                self.add(command)
                return True
        return False

    def r_set(self, command):
        target_rec = self.getVariable(command['target'])
        target = self.getInnerObject(target_rec)
        ctype = command['type']
        if ctype == 'system':
            target.setSystemName(self.textify(command['value']))
        elif ctype == 'heart':
            active = self.textify(command['value'])
            target.setHeartbeat(active not in ('0', ''))
        elif ctype == 'request':
            target.setRequest(self.textify(command['value']))
        elif ctype == 'calling':
            target.setCalling(self.textify(command['value']))
        elif ctype == 'input':
            target.setInput(self.textify(command['value']))
        elif ctype == 'profiles':
            names = self.textify(command['value'])
            selected = int(self.textify(command['selected'])) if 'selected' in command else 0
            try:
                items = json.loads(names) if isinstance(names, str) else names
                names_list = [p.get('name', '') for p in items] if isinstance(items, list) else []
            except (json.JSONDecodeError, TypeError):
                names_list = []
            target.setProfiles(names_list, selected)
        elif ctype == 'rooms':
            rooms = self.textify(command['value'])
            try:
                items = json.loads(rooms) if isinstance(rooms, str) else rooms
                names_list = [r.get('name', '') for r in items] if isinstance(items, list) else []
            except (json.JSONDecodeError, TypeError):
                names_list = []
            target.setRooms(names_list)
        elif ctype == 'days':
            days = self.textify(command['value'])
            try:
                items = json.loads(days) if isinstance(days, str) else days
                days_list = list(items) if isinstance(items, list) else []
            except (json.JSONDecodeError, TypeError):
                days_list = []
            target.setDays(days_list)
        elif ctype == 'profile':
            target.setProfile(self.textify(command['value']))
        elif ctype == 'periods':
            periods = self.textify(command['value'])
            try:
                items = json.loads(periods) if isinstance(periods, str) else periods
                period_list = items if isinstance(items, list) else []
            except (json.JSONDecodeError, TypeError):
                period_list = []
            target.setPeriods(period_list)
        elif ctype == 'calendar':
            target.setCalendar(self.textify(command['value']) == 'on')
        elif ctype == 'title':
            target.setTitle(self.textify(command['value']))
        elif ctype == 'text':
            if isinstance(target, TopBar):
                target.setSystemName(self.textify(command['value']))
            elif hasattr(target, 'setText'):
                target.setText(self.textify(command['value']))
        elif ctype == 'spec':
            spec = self.textify(command['value'])
            try:
                spec_dict = json.loads(spec) if isinstance(spec, str) else spec
            except (json.JSONDecodeError, TypeError):
                spec_dict = {}
            target.render(spec_dict)
        elif ctype == 'temp':
            value = self.textify(command['value'])
            try:
                from rbrwidgets import format_temp
                target.tempLabel.setText(f'{format_temp(value)}°')
            except (AttributeError, ValueError):
                pass
        return self.nextPC()

    ###########################################################################
    # show {rbrwin|sheet} | hide {rbrwin|sheet}

    def k_show(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, (ECRBRWin, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRRoomsSheet, ECRBRCalendarSheet)):
                command['name'] = record['name']
                self.add(command)
                return True
        return False

    def r_show(self, command):
        record = self.getVariable(command['name'])
        widget = self.getInnerObject(record)
        if isinstance(widget, RBRMainWindow):
            # Portrait: maximize so the fixed-size window fills the screen
            # (decorations/frames don't clip it). Landscape: show normally
            # as a centered portrait-shaped window.
            if getattr(widget, 'maximizeOnShow', False):
                widget.showMaximized()
            else:
                widget.show()
        elif isinstance(widget, Sheet):
            window = widget.parentWidget()
            if window is not None:
                window.showSheet(widget)
            else:
                widget.show()
            # Virtual keyboard: pop whenever a sheet with a text input is
            # shown (Add Room, System Name, Request Relay). The keyboard is
            # modal — typing goes into the sheet's field live; tick accepts,
            # cross cancels and restores the field's original content. The
            # sheet's panel is raised above the keyboard first so the input
            # and its Save/Cancel rows stay visible.
            if hasattr(widget, 'input'):
                from allspeak.as_keyboard import Keyboard, TextReceiver, Border, VirtualKeyboard
                from PySide6.QtWidgets import QDialog, QVBoxLayout
                # Measure the keyboard's height with the same content the
                # runtime builds (fonts/scale-correct), then float the panel
                # above it.
                probe = QDialog()
                probe.setFixedWidth(500)
                probeLayout = QVBoxLayout(probe)
                probeLayout.addWidget(Border())
                probeLayout.addWidget(VirtualKeyboard(None, probe.accept))
                probe.adjustSize()
                kb_height = probe.height()
                widget.setKeyboardClearance(kb_height)
                receiver = TextReceiver(widget.input)
                # The field is pre-filled with the current value (system
                # name / relay name). The keypad only appends, so wrap the
                # receiver: the first typed character replaces the pre-filled
                # text instead of producing 'oldtextnewtext'. Ticking without
                # typing keeps the pre-filled value (e.g. request the shown
                # relay).
                receiver = ReplaceFirstReceiver(receiver)
                # Physical typing bypasses the receiver (keys go straight
                # into the field), so give it the same replace-first rule:
                # strip the pre-filled prefix on the first user edit. The
                # keypad's programmatic setText does not fire textEdited, so
                # this hook only triggers for physical input.
                prefill = widget.input.text()

                def on_first_edit(text):
                    if text.startswith(prefill) and len(text) > len(prefill):
                        widget.input.setText(text[len(prefill):])
                    try:
                        widget.input.textEdited.disconnect(on_first_edit)
                    except RuntimeError:
                        pass

                widget.input.textEdited.connect(on_first_edit)
                # The keyboard's modal exec() lets the app's Qt timers run
                # reentrant flushes (refresh, MQTT intents, MainLoop ticks),
                # which overwrite the shared program.pc. Capture it and
                # resume from the same point when the keyboard closes.
                saved_pc = self.program.pc
                kbd = Keyboard(self.program, receiver, window)
                self.program.pc = saved_pc
                widget.setKeyboardClearance(0)
                # The tick (or Enter) means "apply": commit the sheet's Save
                # row so the change ships immediately instead of leaving the
                # edited text sitting in the field waiting for a Save tap.
                if kbd.dialog.result() == QDialog.DialogCode.Accepted:
                    for row in widget.rows:
                        if getattr(row, 'rowId', None) == 'save':
                            row._clicked(row.rowId)
                            break
                else:
                    # The keyboard's ✕ (or Esc) cancelled the edit — treat it
                    # as Cancel of the whole dialog so the prompt sheet
                    # closes too, instead of lingering open over the rooms.
                    for row in widget.rows:
                        if getattr(row, 'rowId', None) == 'cancel':
                            row._clicked(row.rowId)
                            break
                return saved_pc + 1
        return self.nextPC()

    def k_hide(self, command):
        if self.nextIsSymbol():
            record = self.getSymbolRecord()
            if self.isObjectType(record, (ECRBRWin, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRRoomsSheet, ECRBRCalendarSheet)):
                command['name'] = record['name']
                self.add(command)
                return True
        return False

    def r_hide(self, command):
        record = self.getVariable(command['name'])
        widget = self.getInnerObject(record)
        if isinstance(widget, Sheet):
            window = widget.parentWidget()
            if window is not None:
                window.hideSheet(widget)
            else:
                widget.hide()
        else:
            widget.hide()
        return self.nextPC()

    ###########################################################################
    # clear rooms of {rbrwin}

    def k_clear(self, command):
        if self.peek() == 'rooms':
            self.nextToken()
            self.skip('of')
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if self.isObjectType(record, ECRBRWin):
                    command['name'] = record['name']
                    self.add(command)
                    return True
        return False

    def r_clear(self, command):
        record = self.getVariable(command['name'])
        window = self.getInnerObject(record)
        window.clearRooms()
        return self.nextPC()

    ###########################################################################
    # on click {widget} go to {label} — wire a plugin widget's tap to a label

    def k_on(self, command):
        token = self.nextToken()
        command['type'] = token
        if token in ('click', 'tap'):
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if self.isObjectType(record, (ECRBRRoom, ECRBRTopBar, ECRBRProfiles, ECRBRSheet, ECRBRSchedSheet, ECRBRProfileSheet, ECRBRButton)):
                    command['name'] = record['name']
                    self.skip('go')
                    self.skip('to')
                    command['goto'] = self.nextToken()
                    self.add(command)
                    return True
        return False

    def r_on(self, command):
        # The graphics domain compiles `on click {widget} go to {label}` for
        # ECWidget types with domain=this plugin and goto=the handler pc; the
        # handler sequence itself jumps to the label. So `goto` is a pc, not
        # a label name.
        record = self.getVariable(command['name'])
        object = self.getObject(record)
        goto = command['goto']
        widget = self.getInnerObject(object)

        # Store the handler pc on the EC object so r_add can wire each
        # created card (the shared `room` variable only holds the last one).
        object.clickPC = goto

        if isinstance(widget, RoomCard):
            def room_handler(idx, *args):
                # No setIndex here — the shared `room` variable holds a
                # single value (see r_add); the card index travels in the
                # pending dict. Remember the clicked card for `get pending`.
                object.lastClicked = widget
                self.run(goto)
                flush()
            widget.setClickCallback(room_handler)
        elif isinstance(widget, ProfileBar):
            def indexed_handler(idx, *args):
                # Keep the clicked index off the EC `index` cursor — the
                # wrapper's values hold a single widget, so setIndex would
                # crash later getInnerObject calls (values[idx] out of
                # range). r_get 'index' reads `lastIndex`.
                object.lastIndex = idx
                self.run(goto)
                flush()
            widget.setClickCallback(indexed_handler)
        elif isinstance(widget, Sheet):
            def row_handler(row_id, *args):
                self.run(goto)
                flush()
            widget.setClickCallback(row_handler)
        elif isinstance(widget, TopBar):
            def plain_handler(*args):
                self.run(goto)
                flush()
            widget.setClickCallback(plain_handler)
        elif isinstance(widget, WidgetButton):
            def button_handler(*args):
                self.run(goto)
                flush()
            widget.setClickCallback(button_handler)
        return self.nextPC()
