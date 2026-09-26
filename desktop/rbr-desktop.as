!   rbr-desktop.as — the RBR desktop application.
!!
!! A desktop version of the Room-By-Room UI, mirroring the new-ui web PWA
!! (top bar, profile pills, room cards with inline mode control, menu and
!! dialog sheets, per-room schedule editor). Runs as an AllSpeak graphics
!! app (PySide6) and talks to the controller over MQTT via the local
!! mosquitto — on the controller itself (broker `localhost`) or from any
!! computer on the same LAN (broker = the controller's LAN IP). No internet
!! needed.
!!
!! The RBR-specific widgets (rbrwin, topbar, profilesbar, room, sheet) are
!! provided by the rbr_ui.py plugin and live in this project — they are not
!! part of the AllSpeak core pack.
!!
!! Runtime notes: the app keeps its main flow running with a tight wait
!! loop so queued MQTT intents are drained, and it needs three small
!! allspeak-py fixes (see desktop/README.md): the on_connect thread-safety
!! fix, the `plain` clause for non-TLS LAN brokers, and the queueIntent
!! wake-up so an idle program processes incoming intents.
!! @hash
!! @verified
!!!

    script RBRDesktop

    use graphics
    use mqtt
    load plugin RBR_UI from rbr_ui.py

    rbrwin Win
    topbar Bar
    profilesbar Profiles
    profilesheet ProfileSheet
    roomsheet RoomsSheet
    calendarsheet CalendarSheet
    room Room
    sheet Menu
    sheet NameSheet
    sheet RequestSheet
    sheet RoomSheet
    sheet RenameSheet
    sheet AddSheet
    sheet RenameRoomSheet
    sheet AboutSheet
    schedsheet ScheduleSheet

    topic ServerTopic
    topic MyTopic

    dictionary ReceivedMessage
    dictionary Message
    dictionary Map
    dictionary Config
    dictionary Profile
    dictionary RoomSpec
    dictionary Msg
    dictionary Pending
    dictionary NewSpec
    dictionary CalendarDay
    list CalendarData
    list DayNames
    dictionary CalendarPending
    variable CalendarEvent
    variable CalendarDayIdx
    variable CalendarProfileIdx
    variable DayLoop
    variable PropName
    list ProfileList
    list Rooms
    variable Value
    variable ProfileName
    variable L
    variable I
    variable Username
    variable Password
    variable Broker
    variable Port
    variable MAC
    variable MyID
    variable NumberOfRooms
    variable SelectedProfile
    variable SystemName
    variable R
    variable RefreshCount
    variable P
    variable PAction
    variable RoomName
    variable Mode
    variable Action
    variable Duration
    variable Target
    variable AdvanceFlag
    variable RowId
    variable NewValue
    variable RequestRelay
    variable RequestName
    variable BoostUntil
    variable NowMs
    variable BoostRemaining
    variable BoostMinutes
    variable CallingCount
    variable CallingName
    variable CallingText
    variable LastRefresh
    variable RefreshNow
    ! Schedule-editor state (mirrors the web PWA's schedule-editor.as).
    list EditingProfiles
    list EditingPeriods
    list SourcePeriods
    list StoragePeriods
    list NewPeriodsList
    list EditedProfileRooms
    dictionary SourcePeriod
    dictionary ClonedPeriod
    dictionary EditingPeriodRow
    dictionary EditedProfile
    dictionary EditedRoom
    dictionary SchedulePending
    dictionary ProfilePending
    dictionary ProfileSrc
    dictionary RoomPending
    dictionary RoomA
    dictionary RoomB
    dictionary SwapProfile
    list KeptRooms
    list NewProfiles
    list KeptProfiles
    list ProfileRooms
    dictionary ClonedProfile
    variable ProfileEvent
    variable ProfileIdx
    variable ProfileEditIdx
    variable ProfileIndex
    variable ProfileListCount
    variable ProfileLoop
    variable CalendarState
    variable RoomEvent
    variable RoomIdx
    variable SwapIdx
    variable ScheduleEvent
    variable ScheduleField
    variable ScheduleDelta
    variable ScheduleTime
    variable ScheduleMinutes
    variable ScheduleH
    variable ScheduleM
    variable PeriodIdx
    variable PeriodEnabled
    variable PeriodTempTenths
    variable LoopE
    variable SortI
    variable SortJ
    variable SortJplus1
    dictionary PeriodA
    dictionary PeriodB
    variable SortAMinutes
    variable SortBMinutes
    variable EditingPeriodsCount
    variable SourcePeriodsCount
    variable EditingProfileIdx
    variable EditingRoomIdx
    variable SchedProfilePillIdx
    variable ScheduleDirty
    variable ConfirmResult
    variable DotIdx
    variable DecPart
    variable AvgInt
    variable AvgDec

    init graphics

    messagebox DiscardBox
    messagebox DeleteProfileBox
    messagebox CalendarNoticeBox
    messagebox DeleteRoomBox

!! Build the window (PWA-style), the menu sheet and the dialog sheets.

!! @hash
!! @verified
!!!
    create Win title `Room By Room` size 430 800
    create Bar
    create Profiles
    create Menu title `Menu`
    attach Bar to Win
    attach Profiles to Win
    addrow `System type & name` sub `Change the system name` id `system` to Menu
    addrow `Request relay` sub `Ask the boiler to run now` id `request` to Menu
    addrow `Profiles` sub `Add, rename or delete profiles` id `profiles` to Menu
    addrow `Calendar` sub `Which profile runs on each day` id `calendar` to Menu
    addrow `Rooms` sub `Add a room or change the order` id `rooms` to Menu
    addrow `About Room By Room` id `about` to Menu
    add Menu to Win

    create NameSheet title `System name`
    addinput `New system name` to NameSheet
    addrow `Save` id `save` to NameSheet
    addrow `Cancel` id `cancel` to NameSheet
    add NameSheet to Win

    create RequestSheet title `Request relay`
    addinput `Relay name` to RequestSheet
    addrow `Save` id `save` to RequestSheet
    addrow `Cancel` id `cancel` to RequestSheet
    add RequestSheet to Win

    create RoomSheet title `Add room`
    addinput `Room name` to RoomSheet
    addrow `Save` id `save` to RoomSheet
    addrow `Cancel` id `cancel` to RoomSheet
    add RoomSheet to Win

    create RoomsSheet title `Rooms`
    add RoomsSheet to Win

    create ProfileSheet title `Profiles`
    add ProfileSheet to Win

    create CalendarSheet title `Calendar`
    add CalendarSheet to Win

    create RenameSheet title `Rename profile`
    addinput `New name` to RenameSheet
    addrow `Save` id `save` to RenameSheet
    addrow `Cancel` id `cancel` to RenameSheet
    add RenameSheet to Win

    create RenameRoomSheet title `Rename room`
    addinput `New name` to RenameRoomSheet
    addrow `Save` id `save` to RenameRoomSheet
    addrow `Cancel` id `cancel` to RenameRoomSheet
    add RenameRoomSheet to Win

    create AddSheet title `Add profile`
    addinput `Name (copies the active profile's rooms)` to AddSheet
    addrow `Save` id `save` to AddSheet
    addrow `Cancel` id `cancel` to AddSheet
    add AddSheet to Win

    create AboutSheet title `About Room By Room`
    addrow `Version 1.0` id `close` to AboutSheet
    add AboutSheet to Win

    create ScheduleSheet title `Schedule`
    add ScheduleSheet to Win
    create DiscardBox on Win style question title `Discard changes` message `Discard unsaved changes to this profile?`
    create DeleteProfileBox on Win style question title `Delete profile` message `Delete this profile from the list?`
    create CalendarNoticeBox on Win style warning title `Calendar active` message `The calendar chooses the active profile, so manual selection is off. You can still add, rename or delete profiles.`
    create DeleteRoomBox on Win style question title `Delete room` message `Delete this room from every profile?`

    show Win

!! MQTT connection. Read a local config.json if present (broker, port, mac,
!! username, password); otherwise default to running on the controller
!! itself (broker `localhost`). The desktop app is a local/LAN-only client:
!! it always talks plain TCP to a mosquitto on the local network (the
!! controller's `plain` broker on 1883, or `localhost` on the controller
!! itself) — the remote path (cloud broker, TLS 8883) belongs to the web UI.

!! @hash
!! @verified
!!!
    if file `config.json` exists
    begin
        load Config from `config.json`
        if Config has entry `broker` put entry `broker` of Config into Broker
        else put `localhost` into Broker
        if Config has entry `port` put entry `port` of Config into Port
        else put 1883 into Port
        if Config has entry `mac` put entry `mac` of Config into MAC
        else put `c8:21:58:2c:5c:8b` into MAC
        if Config has entry `username` put entry `username` of Config into Username
        else put `rbr` into Username
        ! Display name for the request/demand relay chip (e.g. "Demand");
        ! optional — falls back to the map's raw relay name.
        if Config has entry `requestName` put entry `requestName` of Config into RequestName
        else put empty into RequestName
        ! No password fallback: the LAN mosquitto is allow_anonymous, so a
        ! config-less run connects without credentials. The password is also
        ! the cloud-broker login, so it is never baked into the script.
        if Config has entry `requestName` put entry `requestName` of Config into RequestName
        else put empty into RequestName
    end
    else
    begin
        put `localhost` into Broker
        put 1883 into Port
        put `c8:21:58:2c:5c:8b` into MAC
        put `rbr` into Username
        put empty into RequestName
    end
    put `RBR-desktop-` cat random 999999 into MyID
    put empty into Duration
    put empty into Target
    put empty into AdvanceFlag

    init ServerTopic
        name MAC
        qos 1
    init MyTopic
        name MyID
        qos 1

    mqtt
        token Username Password
        id MyID
        broker Broker
        port Port
        plain
        subscribe MyTopic

    on mqtt connect go to Connected
    on mqtt message go to OnMessage
    on click Room go to RoomClicked
    on click Profiles go to ProfileClicked
    on click Bar go to MenuClicked
    on click Menu go to MenuRowClicked
    on click ProfileSheet go to ProfileSheetClicked
    on click CalendarSheet go to CalendarSheetClicked
    on click RoomsSheet go to RoomsSheetClicked
    on click RenameSheet go to RenameSheetClicked
    on click RenameRoomSheet go to RenameRoomSheetClicked
    on click AddSheet go to AddSheetClicked
    on click NameSheet go to NameSheetClicked
    on click RequestSheet go to RequestSheetClicked
    on click RoomSheet go to RoomSheetClicked
    on click AboutSheet go to AboutSheetClicked
    on click ScheduleSheet go to SchedSheetClicked

!! Keep the main flow running forever so MQTT intents drain (see the doc
!! block at the top). Every ~10 seconds send a read-only `refresh`; the
!! controller replies with the full map only when something changed.

!! @hash
!! @verified
!!!
MainLoop:
    wait 1 tick
    ! Refresh by wall-clock, not tick count: in the graphics context the
    ! wait loop runs far slower than the CLI's 10 ms/tick, so a tick-based
    ! counter would only fire a refresh every few minutes. Every ~10 s send
    ! a read-only `refresh`; the controller replies with the full map only
    ! when something changed.
    if LastRefresh is empty put now into LastRefresh
    put now into RefreshNow
    take LastRefresh from RefreshNow
    if RefreshNow is greater than 10000
    begin
        send to ServerTopic
            sender MyTopic
            action `refresh`
        put now into LastRefresh
    end
    go to MainLoop

!! Connected: request the full map once. Read-only.

!! @hash
!! @verified
!!!
Connected:
    log `rbr-desktop: connected, sending first`
    send to ServerTopic
        sender MyTopic
        action `first`
    stop

!! OnMessage: receive a controller reply and re-render the room list when
!! the reply carries a map.

!! @hash
!! @verified
!!!
OnMessage:
    put the mqtt message into ReceivedMessage
    ! Pulse the heartbeat on EVERY reply — full map or empty heartbeat ping
    ! (the controller replies empty to `refresh` when nothing changed; any
    ! reply proves the round-trip is alive, so the dot cycles on the 10 s
    ! refresh even on a quiet system).
    set heart of Win to 1
    if ReceivedMessage has entry `message`
    begin
        put entry `message` of ReceivedMessage into Message
        if Message is not empty
        begin
            put json Message into Map
            or stop
            gosub to RenderMap
        end
    end
    stop

!! RenderMap: update the system name, request-relay indicator, profile bar
!! and the room cards from the active profile in the map.

!! @hash
!! @verified
!!!
RenderMap:
    put entry `profiles` of Map into ProfileList
    put entry `profile` of Map into SelectedProfile
    gosub to ResolveCalendarProfile
    put entry `name` of Map into SystemName
    set system name of Win to SystemName
    if Map has entry `request` put entry `request` of Map into RequestRelay
    else put empty into RequestRelay
    ! Use the configured display name for the request/demand relay chip when
    ! one is set (e.g. "Demand"); otherwise show the raw relay name.
    if RequestRelay is not empty and RequestName is not empty put RequestName into RequestRelay
    set request of Win to RequestRelay
    set profiles of Profiles to ProfileList selected SelectedProfile
    ! The profile manager sheet mirrors the bar: rows refresh on every map
    ! push so an action's reply re-paints immediately (it may be open under
    ! the rename/add dialogs).
    set profiles of ProfileSheet to ProfileList selected SelectedProfile
    set calendar of ProfileSheet to CalendarState
    ! The calendar editor mirrors the calendar fields; repaint its rows and
    ! day assignments each push.
    set calendar of CalendarSheet to CalendarState
    set profiles of CalendarSheet to ProfileList
    gosub to PaintCalendarDayNames
    set days of CalendarSheet to DayNames

    put item SelectedProfile of ProfileList into Profile
    put entry `rooms` of Profile into Rooms
    ! The room manager mirrors the displayed room list; rows refresh on every
    ! map push so a reorder / add reply re-paints immediately.
    set rooms of RoomsSheet to Rooms
    put the count of Rooms into NumberOfRooms
    log `rbr-desktop: rendering ` cat NumberOfRooms cat ` rooms`
    clear rooms of Win
    ! Calling-for-heat pill: count rooms whose relay is on (a relay is only
    ! on when the controller is calling for heat) and show the PWA-style
    ! summary in the top bar.
    put 0 into CallingCount
    put empty into CallingName
    put 0 into R
    while R is less than NumberOfRooms
    begin
        put item R of Rooms into RoomSpec
        if entry `relay` of RoomSpec is `on`
        begin
            increment CallingCount
            if CallingName is empty put entry `name` of RoomSpec into CallingName
        end
        create Room spec RoomSpec index R
        add Room to Win
        increment R
    end
    if CallingCount is 0 put empty into CallingText
    else if CallingCount is 1 put CallingName cat ` calling for heat` into CallingText
    else put CallingCount cat ` rooms calling for heat` into CallingText
    set calling of Win to CallingText
    stop

!! ResolveCalendarProfile: the controller applies the calendar to pick the
!! active profile (Monday=0 weekday numbering matching calendar-data). The
!! map's `profile` entry is the last manually-selected profile — rendering
!! it directly would show the wrong rooms whenever the calendar overrides
!! (e.g. a weekday when the saved profile is Weekend). Mirror the
!! controller's ResolveCalendarProfile exactly.

!! @hash
!! @verified
!!!
ResolveCalendarProfile:
    put `off` into CalendarState
    if Map has entry `calendar`
    begin
            if entry `calendar` of Map is `on`
        begin
                    put `on` into CalendarState
                    put weekday into Value
                    put entry `calendar-data` of Map into CalendarData
            put item Value of CalendarData into CalendarDay
            if CalendarDay is not empty
            begin
                            put entry `day` cat Value cat `-profile` of CalendarDay into ProfileName
                            put the count of ProfileList into L
                            put 0 into I
                while I is less than L
                begin
                                    put item I of ProfileList into CalendarDay
                    if entry `name` of CalendarDay is ProfileName put I into SelectedProfile
                    increment I
                end
            end
        end
    end
    return

!! RoomClicked: the expansion controls (mode pills, target steppers, boost
!! durations, advance) set a pending action on the card. Dispatch it as an
!! `Operating Mode` uirequest; a plain tap (no pending) just toggled the
!! expansion and needs no action.

!! @hash
!! @verified
!!!
RoomClicked:
    get pending of Room into Pending
    if Pending has entry `action`
    begin
        put entry `action` of Pending into PAction
        put entry `index` of Pending into R
        ! Edit schedule opens the schedule editor for this room instead of
        ! shipping an Operating Mode request.
        if PAction is `editschedule`
        begin
            gosub to OpenScheduleEditor
            stop
        end
        put item R of Rooms into RoomSpec
        put entry `name` of RoomSpec into RoomName
        put entry `mode` of RoomSpec into Mode
        put `Operating Mode` into Action
        if PAction is `mode` put entry `mode` of Pending into Mode
        else if PAction is `boost` put `boost` into Mode
        else if PAction is `advance` put `timed` into Mode
        if PAction is `boost` put entry `duration` of Pending into Duration
        else if PAction is `target` put entry `target` of Pending into Target
        else if PAction is `advance` put `yes` into AdvanceFlag
        ! Target edits during an active boost must resend the remaining
        ! boost minutes: a bare mode=boost with no boost/duration field
        ! makes the controller re-derive until = now and the boost expires
        ! immediately (mirrors the PWA's WriteTargetTenths guard).
        if PAction is `target` and Mode is `boost`
        begin
            if RoomSpec has entry `until`
            begin
                put entry `until` of RoomSpec into BoostUntil
                put now into NowMs
                put BoostUntil into BoostRemaining
                take NowMs from BoostRemaining
                add 59999 to BoostRemaining
                divide BoostRemaining by 60000
                if BoostRemaining is less than 1 put 1 into BoostRemaining
                else if BoostRemaining is greater than 180 put 180 into BoostRemaining
                put BoostRemaining into BoostMinutes
            end
            else put 1 into BoostMinutes
        end
        gosub to SendOperatingMode
    end
    stop

!! ProfileClicked: a profile pill was tapped — switch the active profile.

!! @hash
!! @verified
!!!
ProfileClicked:
    get index of Profiles into P
    put `{}` into Msg
    set entry `Action` of Msg to `Select Profile`
    set entry `Profile` of Msg to P
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Msg
    stop

!! Profile manager (menu → Profiles). The ProfileSheet lists every profile:
!! row tap = select active, ✎ = rename, ✕ = delete, and the Add button clones
!! the active profile under a new name. Edits apply immediately — each action
!! ships one `Update Profiles` uirequest (profile + calendar unchanged unless
!! the action must re-index the manual selection) and the controller's reply
!! re-renders the sheet. While the calendar is on, row taps are blocked with
!! a notice (calendar editing arrives in a later phase).

!! @hash
!! @verified
!!!
ProfileSheetClicked:
    get pending of ProfileSheet into ProfilePending
    if ProfilePending has entry `event`
    begin
        put entry `event` of ProfilePending into ProfileEvent
        if ProfileEvent is `select`
        begin
            put entry `index` of ProfilePending into ProfileIdx
            gosub to SelectProfileFromSheet
        end
        else if ProfileEvent is `up` or ProfileEvent is `down`
        begin
            put entry `index` of ProfilePending into ProfileIdx
            put ProfileIdx into SwapIdx
            if ProfileEvent is `up` take 1 from SwapIdx
            else increment SwapIdx
            if SwapIdx is not less than 0 gosub to SwapAdjacentProfiles
        end
        else if ProfileEvent is `rename`
        begin
            put entry `index` of ProfilePending into ProfileIdx
            put ProfileIdx into ProfileEditIdx
            gosub to OpenRenameSheet
        end
        else if ProfileEvent is `delete`
        begin
            put entry `index` of ProfilePending into ProfileIdx
            put ProfileIdx into ProfileEditIdx
            show DeleteProfileBox giving ConfirmResult
            if ConfirmResult is `Yes` gosub to DeleteProfileNow
        end
        else if ProfileEvent is `add`
        begin
            set input of AddSheet to empty
            show AddSheet
        end
    end
    stop

!! @hash
!! @verified
!!!
SelectProfileFromSheet:
    if CalendarState is `on`
    begin
        show CalendarNoticeBox giving ConfirmResult
        return
    end
    if ProfileIdx is SelectedProfile return
    put `{}` into Msg
    set entry `Action` of Msg to `Select Profile`
    set entry `Profile` of Msg to ProfileIdx
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Msg
    return

!! SwapAdjacentProfiles: swap the profile at ProfileIdx with the one at
!! SwapIdx and ship the reordered list. Reordering is index-based, so the
!! manual `profile` selection follows the moved profile — the calendar maps
!! by profile NAME, so day assignments ride along unchanged.

!! @hash
!! @verified
!!!
SwapAdjacentProfiles:
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    if SwapIdx is not less than ProfileListCount return
    put item ProfileIdx of NewProfiles into ProfileSrc
    put item SwapIdx of NewProfiles into SwapProfile
    set item ProfileIdx of NewProfiles to SwapProfile
    set item SwapIdx of NewProfiles to ProfileSrc
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    if ProfileIndex is ProfileIdx put SwapIdx into ProfileIndex
    else if ProfileIndex is SwapIdx put ProfileIdx into ProfileIndex
    log `rbr-desktop: reorder profiles ` cat ProfileIdx cat ` and ` cat SwapIdx
    gosub to ShipProfilesUpdate
    return

!! @hash
!! @verified
!!!
OpenRenameSheet:
    put item ProfileEditIdx of ProfileList into ProfileSrc
    put entry `name` of ProfileSrc into ProfileName
    set input of RenameSheet to ProfileName
    show RenameSheet
    return

!! @hash
!! @verified
!!!
RenameSheetClicked:
    get row of RenameSheet into RowId
    if RowId is `save`
    begin
        get input of RenameSheet into NewValue
        if NewValue is not empty gosub to RenameProfileNow
    end
    hide RenameSheet
    stop

!! @hash
!! @verified
!!!
RenameProfileNow:
    put ProfileList into NewProfiles
    put item ProfileEditIdx of NewProfiles into ProfileSrc
    set entry `name` of ProfileSrc to NewValue
    set item ProfileEditIdx of NewProfiles to ProfileSrc
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    gosub to ShipProfilesUpdate
    return

!! @hash
!! @verified
!!!
AddSheetClicked:
    get row of AddSheet into RowId
    if RowId is `save`
    begin
        get input of AddSheet into NewValue
        if NewValue is not empty gosub to AddProfileNow
    end
    hide AddSheet
    stop

!! AddProfileNow: append a profile named NewValue cloned from the active
!! (calendar-resolved) profile, so the new profile inherits the same rooms
!! and schedules. The manual selection is untouched (the PWA behaves the
!! same — AddEditProfile clones and appends without selecting).

!! @hash
!! @verified
!!!
AddProfileNow:
    put ProfileList into NewProfiles
    put item SelectedProfile of NewProfiles into ProfileSrc
    put `{}` into ClonedProfile
    set entry `name` of ClonedProfile to NewValue
    put entry `rooms` of ProfileSrc into ProfileRooms
    set entry `rooms` of ClonedProfile to ProfileRooms
    append ClonedProfile to NewProfiles
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    gosub to ShipProfilesUpdate
    return

!! DeleteProfileNow: rebuild NewProfiles without ProfileEditIdx and re-index
!! the manual selection — deleting an earlier profile shifts the rest up;
!! deleting the selected profile itself falls back to the entry that slid
!! into its place (clamped to the end). The last profile cannot be deleted.

!! @hash
!! @verified
!!!
DeleteProfileNow:
    put the count of ProfileList into ProfileListCount
    if ProfileListCount is less than 2 return
    put `[]` into KeptProfiles
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        if ProfileLoop is not ProfileEditIdx
        begin
            put item ProfileLoop of ProfileList into ProfileSrc
            append ProfileSrc to KeptProfiles
        end
        increment ProfileLoop
    end
    put KeptProfiles into NewProfiles
    put the count of KeptProfiles into ProfileListCount
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    if ProfileEditIdx is less than ProfileIndex take 1 from ProfileIndex
    put ProfileListCount into ProfileLoop
    take 1 from ProfileLoop
    if ProfileIndex is greater than ProfileLoop put ProfileLoop into ProfileIndex
    gosub to ShipProfilesUpdate
    return

!! ShipProfilesUpdate: send NewProfiles with the manual profile index and
!! the calendar unchanged. Shared by rename / delete / add.

!! @hash
!! @verified
!!!
ShipProfilesUpdate:
    put `{}` into Msg
    set entry `Action` of Msg to `Update Profiles`
    set entry `profiles` of Msg to NewProfiles
    set entry `profile` of Msg to ProfileIndex
    if Map has entry `calendar` set entry `calendar` of Msg to entry `calendar` of Map
    if Map has entry `calendar-data` set entry `calendar-data` of Msg to entry `calendar-data` of Map
    log `rbr-desktop: update profiles`
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Msg
    return

!! Calendar editor (menu → Calendar). CalendarSheet shows an ON/OFF toggle
!! and one row per weekday (Monday-first). Toggle and day assignments apply
!! immediately: each ships an `Update Profiles` uirequest carrying the
!! (unchanged) profiles + manual profile + the calendar fields. The
!! controller replies with the map, and RenderMap repaints the sheet.

!! @hash
!! @verified
!!!
CalendarSheetClicked:
    get pending of CalendarSheet into CalendarPending
    if CalendarPending has entry `event`
    begin
        put entry `event` of CalendarPending into CalendarEvent
        if CalendarEvent is `toggle` gosub to ToggleCalendar
        else if CalendarEvent is `assign`
        begin
            put entry `day` of CalendarPending into CalendarDayIdx
            put entry `index` of CalendarPending into CalendarProfileIdx
            gosub to AssignCalendarDay
        end
    end
    stop

!! @hash
!! @verified
!!!
ToggleCalendar:
    if CalendarState is `on` put `off` into CalendarState
    else put `on` into CalendarState
    gosub to CloneCalendarDataForEdit
    gosub to ShipCalendarUpdate
    return

!! AssignCalendarDay: set the day-CalendarDayIdx assignment to the profile at
!! CalendarProfileIdx (by name — calendar-data holds names, so reordering or
!! renaming profiles never rewrites it).

!! @hash
!! @verified
!!!
AssignCalendarDay:
    if CalendarDayIdx is less than 0 return
    if CalendarDayIdx is greater than 6 return
    put the count of ProfileList into Value
    if CalendarProfileIdx is not less than Value return
    gosub to CloneCalendarDataForEdit
    put item CalendarProfileIdx of ProfileList into ProfileSrc
    put entry `name` of ProfileSrc into ProfileName
    put item CalendarDayIdx of CalendarData into CalendarDay
    if CalendarDay is empty put `{}` into CalendarDay
    set entry `day` cat CalendarDayIdx cat `-profile` of CalendarDay to ProfileName
    set item CalendarDayIdx of CalendarData to CalendarDay
    log `rbr-desktop: calendar day ` cat CalendarDayIdx cat ` = ` cat ProfileName
    gosub to ShipCalendarUpdate
    return

!! CloneCalendarDataForEdit: snapshot the map's calendar-data into
!! CalendarData, padding to 7 day entries (controllers can send a short
!! array on first install before any per-day assignment).

!! @hash
!! @verified
!!!
CloneCalendarDataForEdit:
    if Map has entry `calendar-data` put entry `calendar-data` of Map into CalendarData
    else put `[]` into CalendarData
    put the count of CalendarData into Value
    while Value is less than 7
    begin
        put `{}` into CalendarDay
        append CalendarDay to CalendarData
        increment Value
    end
    return

!! PaintCalendarDayNames: rebuild DayNames (7 display names, '' = none) from
!! the map's calendar-data for the sheet's day rows.

!! @hash
!! @verified
!!!
PaintCalendarDayNames:
    put `[]` into DayNames
    if Map has entry `calendar-data` put entry `calendar-data` of Map into CalendarData
    else put `[]` into CalendarData
    put 0 into DayLoop
    while DayLoop is less than 7
    begin
        put empty into PropName
        put the count of CalendarData into Value
        if DayLoop is less than Value
        begin
            put item DayLoop of CalendarData into CalendarDay
            put `day` cat DayLoop cat `-profile` into Value
            if CalendarDay is not empty
            begin
                if CalendarDay has entry Value put entry Value of CalendarDay into PropName
            end
        end
        append PropName to DayNames
        increment DayLoop
    end
    return

!! ShipCalendarUpdate: ship the calendar change — profiles + manual profile
!! unchanged, calendar on/off + the edited calendar-data. CalendarState and
!! CalendarData are set by the caller.

!! @hash
!! @verified
!!!
ShipCalendarUpdate:
    put `{}` into Msg
    set entry `Action` of Msg to `Update Profiles`
    put ProfileList into NewProfiles
    set entry `profiles` of Msg to NewProfiles
    if Map has entry `profile` set entry `profile` of Msg to entry `profile` of Map
    else set entry `profile` of Msg to 0
    set entry `calendar` of Msg to CalendarState
    set entry `calendar-data` of Msg to CalendarData
    log `rbr-desktop: calendar ` cat CalendarState
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Msg
    return

!! MenuClicked: the hamburger was tapped — show the menu sheet.

!! @hash
!! @verified
!!!
MenuClicked:
    show Menu
    stop

!! MenuRowClicked: route a menu row to its dialog sheet.

!! @hash
!! @verified
!!!
MenuRowClicked:
    get row of Menu into RowId
    hide Menu
    if RowId is `system`
    begin
        set input of NameSheet to SystemName
        show NameSheet
    end
    else if RowId is `request`
    begin
        set input of RequestSheet to RequestRelay
        show RequestSheet
    end
    else if RowId is `profiles` show ProfileSheet
    else if RowId is `calendar` show CalendarSheet
    else if RowId is `rooms` show RoomsSheet
    else if RowId is `about` show AboutSheet
    stop

!! Dialog handlers: Save ships the uirequest, Cancel just closes. The
!! controller replies with the updated map, which re-renders the UI.

!! @hash
!! @verified
!!!
NameSheetClicked:
    get row of NameSheet into RowId
    if RowId is `save`
    begin
        get input of NameSheet into NewValue
        if NewValue is not empty
        begin
            put `{}` into Msg
            set entry `Action` of Msg to `System Name`
            set entry `System Name` of Msg to NewValue
            send to ServerTopic
                sender MyTopic
                action `uirequest`
                message Msg
        end
    end
    hide NameSheet
    stop

!! @hash
!! @verified
!!!
RequestSheetClicked:
    get row of RequestSheet into RowId
    if RowId is `save`
    begin
        get input of RequestSheet into NewValue
        if NewValue is not empty
        begin
            put `{}` into Msg
            set entry `Action` of Msg to `Request Relay`
            set entry `Request Relay` of Msg to NewValue
            send to ServerTopic
                sender MyTopic
                action `uirequest`
                message Msg
        end
    end
    hide RequestSheet
    stop

!! @hash
!! @verified
!!!
RoomSheetClicked:
    get row of RoomSheet into RowId
    if RowId is `save`
    begin
        get input of RoomSheet into NewValue
        if NewValue is not empty gosub to AddRoomToAllProfiles
    end
    hide RoomSheet
    stop

!! Room manager (menu → Rooms). RoomsSheet lists the displayed rooms; ↑/↓
!! reorder and + Add room opens the name dialog (RoomSheet). Both apply
!! immediately and across EVERY profile — RBR keeps one parallel room list
!! per profile (each profile holds its own mode/schedule state per room), so
!! a reorder swaps whole room entries in every profile's rooms array and an
!! add appends the same new room to every profile. One `Update Profiles`
!! uirequest ships the full profiles array (profile + calendar unchanged).

!! @hash
!! @verified
!!!
RoomsSheetClicked:
    get pending of RoomsSheet into RoomPending
    if RoomPending has entry `event`
    begin
        put entry `event` of RoomPending into RoomEvent
        if RoomEvent is `up` or RoomEvent is `down`
        begin
            put entry `index` of RoomPending into RoomIdx
            put RoomIdx into SwapIdx
            if RoomEvent is `up` take 1 from SwapIdx
            else increment SwapIdx
            if SwapIdx is not less than 0 gosub to SwapRoomsInAllProfiles
        end
        else if RoomEvent is `rename`
        begin
            put entry `index` of RoomPending into RoomIdx
            gosub to OpenRenameRoomSheet
        end
        else if RoomEvent is `delete`
        begin
            put entry `index` of RoomPending into RoomIdx
            show DeleteRoomBox giving ConfirmResult
            if ConfirmResult is `Yes` gosub to DeleteRoomFromAllProfiles
        end
        else if RoomEvent is `add`
        begin
            set input of RoomSheet to empty
            show RoomSheet
        end
    end
    stop

!! @hash
!! @verified
!!!
SwapRoomsInAllProfiles:
    ! Guard: the swap partner must exist in the room list. The widget already
    ! disables the end arrows, so this is belt-and-braces.
    put the count of Rooms into Value
    if SwapIdx is not less than Value return
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put item RoomIdx of EditedProfileRooms into RoomA
        put item SwapIdx of EditedProfileRooms into RoomB
        set item RoomIdx of EditedProfileRooms to RoomB
        set item SwapIdx of EditedProfileRooms to RoomA
        set entry `rooms` of EditedProfile to EditedProfileRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    log `rbr-desktop: swap rooms ` cat RoomIdx cat ` and ` cat SwapIdx cat ` in all profiles`
    gosub to ShipProfilesUpdate
    return

!! @hash
!! @verified
!!!
AddRoomToAllProfiles:
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        ! A fresh dict per profile (append stores a reference — never mutate
        ! a symbol after appending it).
        put `{}` into NewSpec
        set entry `name` of NewSpec to NewValue
        set entry `sensor` of NewSpec to empty
        set entry `relays` of NewSpec to `[]`
        set entry `mode` of NewSpec to `off`
        set entry `target` of NewSpec to 20
        set entry `events` of NewSpec to `[]`
        set entry `relayType` of NewSpec to `Zigbee`
        set entry `protect` of NewSpec to `no`
        set entry `linked` of NewSpec to `yes`
        set entry `advance` of NewSpec to `-`
        set entry `prevmode` of NewSpec to `off`
        set entry `relay` of NewSpec to `off`
        set entry `status` of NewSpec to `good`
        set entry `temperature` of NewSpec to -1
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        append NewSpec to EditedProfileRooms
        set entry `rooms` of EditedProfile to EditedProfileRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    log `rbr-desktop: add room ` cat NewValue cat ` to all profiles`
    gosub to ShipProfilesUpdate
    return

!! OpenRenameRoomSheet: pre-fill the rename dialog with the room's current
!! name (RoomIdx is the rename target across the dialog).

!! @hash
!! @verified
!!!
OpenRenameRoomSheet:
    put item RoomIdx of Rooms into RoomSpec
    put entry `name` of RoomSpec into RoomName
    set input of RenameRoomSheet to RoomName
    show RenameRoomSheet
    return

!! @hash
!! @verified
!!!
RenameRoomSheetClicked:
    get row of RenameRoomSheet into RowId
    if RowId is `save`
    begin
        get input of RenameRoomSheet into NewValue
        if NewValue is not empty gosub to RenameRoomInAllProfiles
    end
    hide RenameRoomSheet
    stop

!! RenameRoomInAllProfiles: set the name of room RoomIdx in EVERY profile to
!! NewValue, then ship. The parallel lists stay in sync.

!! @hash
!! @verified
!!!
RenameRoomInAllProfiles:
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put item RoomIdx of EditedProfileRooms into RoomSpec
        set entry `name` of RoomSpec to NewValue
        set item RoomIdx of EditedProfileRooms to RoomSpec
        set entry `rooms` of EditedProfile to EditedProfileRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    log `rbr-desktop: rename room to ` cat NewValue
    gosub to ShipProfilesUpdate
    return

!! DeleteRoomFromAllProfiles: remove room RoomIdx from EVERY profile's rooms
!! array, then ship. The last room is protected (like the last profile).

!! @hash
!! @verified
!!!
DeleteRoomFromAllProfiles:
    put the count of Rooms into Value
    if Value is less than 2 return
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put the count of EditedProfileRooms into Value
        put `[]` into KeptRooms
        put 0 into SwapIdx
        put 0 into Value
        while SwapIdx is less than the count of EditedProfileRooms
        begin
            if SwapIdx is not RoomIdx
            begin
                put item SwapIdx of EditedProfileRooms into RoomSpec
                append RoomSpec to KeptRooms
                increment Value
            end
            increment SwapIdx
        end
        set entry `rooms` of EditedProfile to KeptRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    put entry `profile` of Map into ProfileIndex
    if ProfileIndex is empty put 0 into ProfileIndex
    log `rbr-desktop: delete room ` cat RoomIdx cat ` from all profiles`
    gosub to ShipProfilesUpdate
    return

!! @hash
!! @verified
!!!
AboutSheetClicked:
    hide AboutSheet
    stop

!! OpenScheduleEditor: open the schedule editor for the room at index R in
!! the currently displayed (calendar-resolved) profile. Snapshots ALL
!! profiles into EditingProfiles (the symbol read deep-copies, so cancelling
!! can never leak edits into the live map), clones the room's periods into
!! the display shape {start, off, target}, and renders the sheet. Save
!! ships an `Update Profiles` uirequest with the edited profiles.

!! @hash
!! @verified
!!!
OpenScheduleEditor:
    put item R of Rooms into RoomSpec
    put entry `name` of RoomSpec into RoomName
    put ProfileList into EditingProfiles
    put SelectedProfile into EditingProfileIdx
    put R into EditingRoomIdx
    clear ScheduleDirty
    set title of ScheduleSheet to `Schedule for ` cat RoomName
    put item EditingProfileIdx of EditingProfiles into EditedProfile
    put entry `name` of EditedProfile into ProfileName
    set profile of ScheduleSheet to ProfileName
    set profiles of ScheduleSheet to EditingProfiles selected EditingProfileIdx
    gosub to CloneSchedulePeriods
    gosub to RenderSchedulePeriods
    show ScheduleSheet
    stop

!! SchedSheetClicked: drain one queued event from the schedule sheet and
!! dispatch it. The widget is presentation-only; every mutation happens here
!! on the EditingPeriods working copy, re-rendered via set periods.

!! @hash
!! @verified
!!!
SchedSheetClicked:
    get pending of ScheduleSheet into SchedulePending
    if SchedulePending has entry `event`
    begin
        put entry `event` of SchedulePending into ScheduleEvent
        if ScheduleEvent is `step`
        begin
            put entry `period` of SchedulePending into PeriodIdx
            put entry `field` of SchedulePending into ScheduleField
            put entry `delta` of SchedulePending into ScheduleDelta
            gosub to StepSchedulePeriod
        end
        else if ScheduleEvent is `delete`
        begin
            put entry `period` of SchedulePending into PeriodIdx
            gosub to DeleteSchedulePeriod
        end
        else if ScheduleEvent is `toggle`
        begin
            put entry `period` of SchedulePending into PeriodIdx
            put entry `enabled` of SchedulePending into PeriodEnabled
            gosub to ToggleSchedulePeriod
        end
        else if ScheduleEvent is `add` gosub to AddSchedulePeriod
        else if ScheduleEvent is `profile`
        begin
            put entry `index` of SchedulePending into SchedProfilePillIdx
            gosub to SwapEditingProfile
        end
        else if ScheduleEvent is `save` gosub to SaveSchedule
        else if ScheduleEvent is `cancel` hide ScheduleSheet
    end
    stop

!! CloneSchedulePeriods: clone the edited room's periods (storage shape
!! {on, off, temp, enabled}) into EditingPeriods (display shape
!! {start, off, target, enabled}) — a fresh dict per row so edits never bleed
!! back through the snapshot. An absent `enabled` key reads as enabled, so an
!! older map with no flags shows every period switched on.

!! @hash
!! @verified
!!!
CloneSchedulePeriods:
    put `[]` into EditingPeriods
    put item EditingProfileIdx of EditingProfiles into EditedProfile
    put entry `rooms` of EditedProfile into EditedProfileRooms
    put item EditingRoomIdx of EditedProfileRooms into EditedRoom
    if EditedRoom has entry `periods`
    begin
        put entry `periods` of EditedRoom into SourcePeriods
        put the count of SourcePeriods into SourcePeriodsCount
        put 0 into LoopE
        while LoopE is less than SourcePeriodsCount
        begin
            put item LoopE of SourcePeriods into SourcePeriod
            put `{}` into ClonedPeriod
            set entry `start` of ClonedPeriod to entry `on` of SourcePeriod
            set entry `off` of ClonedPeriod to entry `off` of SourcePeriod
            set entry `target` of ClonedPeriod to entry `temp` of SourcePeriod
            set entry `enabled` of ClonedPeriod to true
            if SourcePeriod has entry `enabled`
                set entry `enabled` of ClonedPeriod to entry `enabled` of SourcePeriod
            append ClonedPeriod to EditingPeriods
            increment LoopE
        end
        put SourcePeriodsCount into EditingPeriodsCount
    end
    else put 0 into EditingPeriodsCount
    return

!! RenderSchedulePeriods: paint the EditingPeriods working copy into the
!! sheet's period cards.

!! @hash
!! @verified
!!!
RenderSchedulePeriods:
    set periods of ScheduleSheet to EditingPeriods
    return

!! StepSchedulePeriod: adjust PeriodIdx's ScheduleField by ScheduleDelta.
!! Times step in 15-minute increments (wrapping at 24:00); targets step in
!! 0.5° tenths, clamped to 5.0–30.0°. Sorting happens on Save, not per edit,
!! so a period can drift through midnight without rows jumping.

!! @hash
!! @verified
!!!
StepSchedulePeriod:
    put item PeriodIdx of EditingPeriods into EditingPeriodRow
    if ScheduleField is `start` put entry `start` of EditingPeriodRow into ScheduleTime
    else if ScheduleField is `off` put entry `off` of EditingPeriodRow into ScheduleTime
    else put entry `target` of EditingPeriodRow into ScheduleTime
    if ScheduleField is `target`
    begin
        put ScheduleTime scale 10 into PeriodTempTenths
        add ScheduleDelta to PeriodTempTenths
        if PeriodTempTenths is less than 50 put 50 into PeriodTempTenths
        if PeriodTempTenths is greater than 300 put 300 into PeriodTempTenths
        put PeriodTempTenths into AvgInt
        put PeriodTempTenths modulo 10 into AvgDec
        divide AvgInt by 10
        put AvgInt cat `.` cat AvgDec into ScheduleTime
        set entry `target` of EditingPeriodRow to ScheduleTime
    end
    else
    begin
        gosub to ScheduleParseTime
        add ScheduleMinutes to ScheduleDelta
        if ScheduleDelta is less than 0 add 1440 to ScheduleDelta
        put ScheduleDelta modulo 1440 into ScheduleDelta
        put ScheduleDelta into ScheduleM
        gosub to ScheduleToHHMM
        if ScheduleField is `start` set entry `start` of EditingPeriodRow to ScheduleTime
        else set entry `off` of EditingPeriodRow to ScheduleTime
    end
    set item PeriodIdx of EditingPeriods to EditingPeriodRow
    set ScheduleDirty
    gosub to RenderSchedulePeriods
    return

!! AddSchedulePeriod: append a sensible default period (06:00–08:00 at
!! 21.0°) to the editor. Sorting happens on Save.

!! @hash
!! @verified
!!!
AddSchedulePeriod:
    put `{}` into ClonedPeriod
    set entry `start` of ClonedPeriod to `06:00`
    set entry `off` of ClonedPeriod to `08:00`
    set entry `target` of ClonedPeriod to `21.0`
    set entry `enabled` of ClonedPeriod to true
    append ClonedPeriod to EditingPeriods
    increment EditingPeriodsCount
    set ScheduleDirty
    gosub to RenderSchedulePeriods
    return

!! DeleteSchedulePeriod: rebuild EditingPeriods without PeriodIdx, then
!! re-render the cards.

!! @hash
!! @verified
!!!
DeleteSchedulePeriod:
    put `[]` into NewPeriodsList
    put 0 into LoopE
    while LoopE is less than EditingPeriodsCount
    begin
        if LoopE is not PeriodIdx
        begin
            put item LoopE of EditingPeriods into EditingPeriodRow
            append EditingPeriodRow to NewPeriodsList
        end
        increment LoopE
    end
    put NewPeriodsList into EditingPeriods
    put the count of NewPeriodsList into EditingPeriodsCount
    set ScheduleDirty
    gosub to RenderSchedulePeriods
    return

!! ToggleSchedulePeriod: record the Enabled checkbox's new state (PeriodEnabled)
!! on the row at PeriodIdx and re-render so the model drives the card. Marks the
!! schedule dirty so Cancel / profile switch still confirm before discarding.

!! @hash
!! @verified
!!!
ToggleSchedulePeriod:
    put item PeriodIdx of EditingPeriods into EditingPeriodRow
    set entry `enabled` of EditingPeriodRow to PeriodEnabled
    set item PeriodIdx of EditingPeriods to EditingPeriodRow
    set ScheduleDirty
    gosub to RenderSchedulePeriods
    return

!! SwapEditingProfile: switch the editor to the profile at
!! SchedProfilePillIdx. If the current edit buffer is dirty, confirm before
!! discarding. Re-clones the new profile's periods and repaints.

!! @hash
!! @verified
!!!
SwapEditingProfile:
    if SchedProfilePillIdx is EditingProfileIdx return
    if ScheduleDirty
    begin
        show DiscardBox giving ConfirmResult
        if ConfirmResult is `No` return
    end
    put SchedProfilePillIdx into EditingProfileIdx
    clear ScheduleDirty
    put item EditingProfileIdx of EditingProfiles into EditedProfile
    put entry `name` of EditedProfile into ProfileName
    set profile of ScheduleSheet to ProfileName
    set profiles of ScheduleSheet to EditingProfiles selected EditingProfileIdx
    gosub to CloneSchedulePeriods
    gosub to RenderSchedulePeriods
    return

!! SaveSchedule: sort EditingPeriods by start time, convert each row back to
!! the storage shape {on, off, temp, enabled}, splice the result into
!! EditingProfiles[EditingProfileIdx].rooms[EditingRoomIdx].periods, then
!! ship an `Update Profiles` uirequest (profile + calendar unchanged) so the
!! controller persists and re-pushes the map.
!!
!! NOTE: `profile` ships the map's MANUAL selection, not the resolved
!! SelectedProfile — the user edited the currently-displayed profile and
!! saving must not change which profile shows when the calendar is toggled
!! off (a deliberate divergence from the PWA, which sends the resolved
!! index).

!! @hash
!! @verified
!!!
SaveSchedule:
    gosub to SortSchedulePeriods
    put `[]` into StoragePeriods
    put 0 into LoopE
    while LoopE is less than EditingPeriodsCount
    begin
        put item LoopE of EditingPeriods into EditingPeriodRow
        put `{}` into ClonedPeriod
        set entry `on` of ClonedPeriod to entry `start` of EditingPeriodRow
        set entry `off` of ClonedPeriod to entry `off` of EditingPeriodRow
        set entry `temp` of ClonedPeriod to entry `target` of EditingPeriodRow
        set entry `enabled` of ClonedPeriod to entry `enabled` of EditingPeriodRow
        append ClonedPeriod to StoragePeriods
        increment LoopE
    end
    put item EditingProfileIdx of EditingProfiles into EditedProfile
    put entry `rooms` of EditedProfile into EditedProfileRooms
    put item EditingRoomIdx of EditedProfileRooms into EditedRoom
    set entry `periods` of EditedRoom to StoragePeriods
    set item EditingRoomIdx of EditedProfileRooms to EditedRoom
    set entry `rooms` of EditedProfile to EditedProfileRooms
    set item EditingProfileIdx of EditingProfiles to EditedProfile
    put `{}` into Msg
    set entry `Action` of Msg to `Update Profiles`
    set entry `profiles` of Msg to EditingProfiles
    if Map has entry `profile` set entry `profile` of Msg to entry `profile` of Map
    else set entry `profile` of Msg to SelectedProfile
    if Map has entry `calendar` set entry `calendar` of Msg to entry `calendar` of Map
    if Map has entry `calendar-data` set entry `calendar-data` of Msg to entry `calendar-data` of Map
    hide ScheduleSheet
    log `rbr-desktop: save schedule for ` cat RoomName
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Msg
    stop

!! SortSchedulePeriods: bubble-sort EditingPeriods in place by `start`
!! (minutes since midnight). N is small (typical schedules are ≤6 periods),
!! so simple O(n²) is fine. Called once from SaveSchedule.

!! @hash
!! @verified
!!!
SortSchedulePeriods:
    if EditingPeriodsCount is less than 2 return
    put 0 into SortI
    while SortI is less than EditingPeriodsCount
    begin
        put 0 into SortJ
        while SortJ is less than EditingPeriodsCount
        begin
            put SortJ into SortJplus1
            increment SortJplus1
            if SortJplus1 is less than EditingPeriodsCount
            begin
                put item SortJ of EditingPeriods into PeriodA
                put item SortJplus1 of EditingPeriods into PeriodB
                put entry `start` of PeriodA into ScheduleTime
                gosub to ScheduleParseTime
                put ScheduleMinutes into SortAMinutes
                put entry `start` of PeriodB into ScheduleTime
                gosub to ScheduleParseTime
                put ScheduleMinutes into SortBMinutes
                if SortAMinutes is greater than SortBMinutes
                begin
                    set item SortJ of EditingPeriods to PeriodB
                    set item SortJplus1 of EditingPeriods to PeriodA
                end
            end
            increment SortJ
        end
        increment SortI
    end
    return

!! ScheduleParseTime: parse ScheduleTime ("HH:MM" or "H:MM") into minutes
!! since midnight -> ScheduleMinutes. Empty / malformed input yields 0.

!! @hash
!! @verified
!!!
ScheduleParseTime:
    put 0 into ScheduleMinutes
    if ScheduleTime is empty return
    put the index of `:` in ScheduleTime into DotIdx
    if DotIdx is less than 0 return
    put the value of left DotIdx of ScheduleTime into ScheduleMinutes
    multiply ScheduleMinutes by 60
    increment DotIdx
    put the value of from DotIdx of ScheduleTime into DecPart
    add DecPart to ScheduleMinutes
    return

!! ScheduleToHHMM: convert ScheduleM (0–1439 minutes since midnight) into
!! "HH:MM" -> ScheduleTime, zero-padded on both fields.

!! @hash
!! @verified
!!!
ScheduleToHHMM:
    put ScheduleM into ScheduleH
    divide ScheduleH by 60
    put ScheduleM modulo 60 into ScheduleM
    if ScheduleH is less than 10 put `0` cat ScheduleH into ScheduleTime
    else put ScheduleH cat empty into ScheduleTime
    put ScheduleTime cat `:` into ScheduleTime
    if ScheduleM is less than 10 put ScheduleTime cat `0` cat ScheduleM into ScheduleTime
    else put ScheduleTime cat ScheduleM into ScheduleTime
    return

!! SendOperatingMode: ship the pending room action as an `Operating Mode`
!! uirequest. Only the fields that apply are included.

!! @hash
!! @verified
!!!
SendOperatingMode:
    put `{}` into Msg
    set entry `Action` of Msg to Action
    set entry `Room` of Msg to RoomName
    set entry `Mode` of Msg to Mode
    if Duration is not empty set entry `duration` of Msg to Duration
    else if BoostMinutes is not empty set entry `boost` of Msg to `B` cat BoostMinutes
    else if Target is not empty set entry `target` of Msg to Target
    else if AdvanceFlag is not empty set entry `advance` of Msg to AdvanceFlag
    put empty into Duration
    put empty into Target
    put empty into AdvanceFlag
    put empty into BoostMinutes
    log `rbr-desktop: send ` cat Msg
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Msg
    stop
