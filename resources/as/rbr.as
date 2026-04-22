!	Room By Room 
!	This is the main program for the RBR Heating user interface. It maintains the screen,
!	populating it with information loaded from the website, and it calls other modules as they are needed.

	script RBR

    div Body
    div MainPanel
    div Mask
    div BannerMask
    div TitleMask
    div SystemTitlePanel
    div SystemNamePanel
    div OuterPanel
    div HelpPanel
    div StatisticsPanel
    div RoomNamePanel
    div RoomTempPanel
    div RoomToolsButton
    div RoomStatusButton
    div ModePanel
    div ModeHolder
    div TargetTemp
    div BoostName
    div ModeText
    div ModeInfo
    div Alive
    div Banner
    div Snowflake
    div Date
    div VersionNumber
    div StatusFlag
    input Input
    img StatisticsIcon
    img CalendarIcon
    img Hamburger
    img ModeIcon
    img Hourglass
    button ProfilesButton
    button AddButton
    button GetSystemNameButton
    button GetRequestButton
    button ModeButton
    button OKButton
    button CancelButton
    module ProfileModule
    module Storyteller
    topic ServerTopic
    topic MyTopic
    variable Mobile
    variable Prompt
    variable Webson
    variable HelpScript
    variable ModeScript
    variable Script
    variable MyID
    variable SystemName
    variable CurrentProfile
    variable Profiles
    variable Profile
    variable RequestIP
    variable Map
    variable Rooms
    variable RoomSpec
    variable RoomCount
    variable RoomIndex
    variable ClickIndex
    variable MQTTWait
    variable CycleWait
    variable Redraw
    variable Refresh
    variable SensorIP
    variable Relays
    variable RelayState
    variable RelayType
    variable Temperature
    variable StaticData
    variable RoomData
    variable RoomName
    variable RoomStatus
    variable Timestamp
    variable IsAlive
    variable Battery
    variable Color
    variable Events
    variable Event
    variable Event2
    variable Blocked
    variable Mode
    variable Flag
    variable Error
    variable SID
    variable TID
    variable Result
    variable Request
    variable RequestData
    variable Finish
    variable ReceivedMessage
    variable Name
    variable TVal
    variable Elapsed
    variable Boost
    variable Advance
    variable Now
    variable UntilTime
    variable UntilTemp
    variable Waiting
    variable Flashing
    variable Flashes
    variable Value
    variable SendOK
    variable NGood
    variable NBad
    variable FH
    variable FM
    variable NR
    variable E
    variable F
    variable H
    variable M
    variable N
    variable R
    variable T

    ! Webson specs
    variable MainScreenWebson
    variable MainMenuWebson
    variable RoomWebson
    variable RoomToolsMenuWebson
    variable GetNameWebson
    variable GetRequestWebson
    variable TimedWebson
    variable BoostWebson
    variable OnWebson
    variable OffWebson
    variable NoneWebson
    variable UseKeyboard
    button KeyboardButton

!    debug step

!   Set up MQTT

    variable Credentials
    variable Broker
    variable Port
    variable Username
    variable Password
    variable MAC
    
    no cache

    if the hostname is `localhost`
    or the hostname starts with `192.168.`
    or the hostname starts with `10.`
    begin
        if the location includes `?login` go to DoLogin
!       Try local credentials file (provided by setup-local-ui.sh)
        rest get Credentials from `credentials.json`
        if Credentials is not empty
        begin
            put property `broker` of Credentials into Broker
            put property `port` of Credentials into Port
            put property `username` of Credentials into Username
            put property `password` of Credentials into Password
            put property `mac` of Credentials into MAC
!           When accessing via IP, use the page hostname as broker
            if Broker is `localhost`
            begin
                if the hostname is not `localhost` put the hostname into Broker
            end
            if Broker is not empty go to MQTTReady
        end
!       Fall back to manual entry for dev use
        get Broker from storage as `dev-broker`
        if Broker is `null` put empty into Broker
        if Broker is `undefined` put empty into Broker
        get Username from storage as `dev-username`
        if Username is `null` put empty into Username
        if Username is `undefined` put empty into Username
        get Password from storage as `dev-password`
        if Password is `null` put empty into Password
        if Password is `undefined` put empty into Password
        get MAC from storage as `dev-mac`
        if MAC is `null` put empty into MAC
        if MAC is `undefined` put empty into MAC
        if Broker is empty
        begin
            put prompt `Dev credentials:` cat newline cat `MQTT Broker URL:` into Broker
            put prompt `Dev credentials:` cat newline cat `Username:` into Username
            put prompt `Dev credentials:` cat newline cat `Password:` into Password
            put prompt `Dev credentials:` cat newline cat `Controller MAC address:` into MAC
            if Broker is empty go to AbandonShip
            put Broker into storage as `dev-broker`
            put Username into storage as `dev-username`
            put Password into storage as `dev-password`
            put MAC into storage as `dev-mac`
        end
        go to MQTTReady
    end

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
DoLogin:
!   Run login/registration flow - exits back here when authenticated
    variable LoginScript
    rest get LoginScript from `resources/as/login.as?v=` cat now
    run LoginScript
!   User is now authenticated - get MQTT credentials from server
    rest get Credentials from `credentials` or rest get Credentials from `credentials.php`
        or go to AbandonShip
!    log Credentials
    put property `broker` of Credentials into Broker
    put property `username` of Credentials into Username
    put property `password` of Credentials into Password
    get MAC from storage as `rbr-mac`
    if MAC is `null` clear MAC
    if MAC is `undefined` clear MAC
    if MAC is empty
    begin
        put prompt `Enter your controller MAC address:` into MAC
        if MAC is empty go to AbandonShip
        put MAC into storage as `rbr-mac`
    end

MQTTReady:

    if Port is empty put 443 into Port
    put `RBR-` cat random 999999 into MyID
!    log `Broker is ` cat Broker
!    log `MAC is ` cat MAC
!    log `Password is ` cat Password
!    log `MyID is ` cat MyID

	init ServerTopic
        name MAC
        qos 1

    init MyTopic
        name MyID
        qos 1

    dummy
    mqtt
        token `rbr` Password
        id MyID
        broker Broker
        port Port
        subscribe MyTopic

    on mqtt connect
    begin
        log `MQTT Connected`
        go to Connected
    end
    
    ! Handle incoming messages
    on mqtt message
    begin
        put the mqtt message into ReceivedMessage
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Connected:
    ! Do the basic setup of the main window
	gosub to SetupScreen

    on resume
    begin
        log `Tab resumed; restarting cycle`
        put 0 into CycleWait
    end

Conn2:
	! Refresh the UI every 10 seconds
    ! If Prompt is set to 'first' deal with it immediately
    while true
    begin
        put 10 into CycleWait
        while CycleWait is not 0
        begin
            wait 1 second
            if not Blocked
            begin
                if Prompt is `first` or ReceivedMessage is not empty
                begin
                    fork to MainProcessingTask
                    go to Conn2
                end
            end
            take 1 from CycleWait
        end
    	if not Blocked fork to MainProcessingTask
    end

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SetupScreen:
    log `Set up the screen...`
    set Redraw
    put empty into ModeScript
    put `first` into Prompt

    set the title to `RBR`

    clear Mobile
    if mobile
    begin
!    	log `Mobile browser detected`
        if portrait
        begin
!        	log `In portrait mode`
        	set Mobile
        end
    end
!    else log `PC browser detected`

    get StaticData from storage as `StaticData`
    if StaticData is empty put `{}` into StaticData
!    log StaticData

	create Body
    if Mobile
    begin
    	set style `width` of Body to `100%`
    end
    else
    begin
        put the height of the window into H
        multiply H by 9 giving N
        divide N by 16
    	set style `width` of Body to N cat `px`
        set style `margin` of Body to `0 auto`
        set style `border` of Body to `1px solid lightgray`
    end
    set style `height` of Body to `calc(100vh - 1em)`
!    put empty into storage as `MAC`

!	First get EasyCoder scripts and the various layout scripts
    put empty into HelpScript

    put empty into MainMenuWebson
    put empty into RoomWebson
    put empty into RoomToolsMenuWebson
    put empty into GetNameWebson
    put empty into GetRequestWebson
    put empty into TimedWebson
    put empty into OnWebson
    put empty into OffWebson
    put empty into NoneWebson

!	Render the main screen layout
    rest get MainScreenWebson from `resources/webson/rbr.json?v=` cat now
    	or go to AbandonShip
	render MainScreenWebson in Body
    attach Hourglass to `hourglass`
    attach Mask to `top-level-mask`
    attach BannerMask to `banner-mask`
    attach TitleMask to `title-mask`
    attach Banner to `rbr-banner`
    attach SystemTitlePanel to `system-title`
    attach SystemNamePanel to `system-name`
    attach MainPanel to `mainpanel`
    attach OuterPanel to `outerpanel`
    attach HelpPanel to `helppanel`
    attach StatisticsPanel to `statisticspanel`
    attach Alive to `alive`
    attach ModePanel to `mode-panel`
    attach StatisticsIcon to `statistics-icon`
    attach CalendarIcon to `calendar-icon`
    attach Date to `calendar-date`
    attach Hamburger to `hamburger-icon`
    attach ProfilesButton to `profile-button`

!	Set up the statistics and hamburger icons
    on click StatisticsIcon
    begin
    	if Storyteller is running
        begin
        	close Storyteller
            set style `display` of OuterPanel to `block`
            set style `display` of HelpPanel to `none`
            clear MainPanel
            clear Blocked
            set Redraw
        end
        else if not Blocked go to Statistics
    end
    on click Hamburger
    begin
    	if Storyteller is running
        begin
        	close Storyteller
            set style `display` of OuterPanel to `block`
            set style `display` of HelpPanel to `none`
            clear MainPanel
            clear Blocked
            set Redraw
        end
        else if not Blocked go to ShowMenu
    end
    log `Screen is ready`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Redraw the UI from the cached Map (no MQTT round-trip needed)
RedrawFromMap:
    set Blocked
    put 0 into RoomCount
    go to ContinueAfterName

!	Main Processing Task
MainProcessingTask:
    if Blocked stop
    set Blocked
    log `MainProcessingTask started`
    gosub to Unmask
	if not Redraw go to GetMap
    put 0 into RoomCount
    clear Error
!    put `System healthy` into SystemStatus

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Get the map
GetMap:
!    if Prompt is `first` log `Get the map for the first time`
!    else log `Get the map`
    if ReceivedMessage is empty
    begin
        log `Send ` cat Prompt
        send to ServerTopic
            sender MyTopic
            action Prompt
        if Prompt is not `first`
        begin
            clear Blocked
            stop
        end
        put 50 into MQTTWait
        while ReceivedMessage is empty
        begin
            wait 10 ticks
            take 1 from MQTTWait
            if MQTTWait is 0
            begin
                log `Timeout waiting for controller response`
                clear Blocked
                stop
            end
        end
    end
    put ReceivedMessage into Map
    log `Got an updated map`
    if Map is empty
    begin
        if Prompt is `first`
        begin
    	    log `Map not available; using local data`
    	    get Map from storage as `map`
       	    continue
        end
        else
        begin
            clear Blocked
            stop
        end
    end
    put `refresh` into Prompt

    if Map is empty gosub to CreateDefaultMap
    if ReceivedMessage is not empty set Redraw
    put empty into ReceivedMessage

    ! Validate the map has essential fields; restore from backup if incomplete
    gosub to ValidateMap

    put Map into storage as `map`

    put property `name` of Map into SystemName
    replace `%20` with ` ` in SystemName

    if SystemName is empty
    begin
        get SystemName from storage as `SystemName`
        if SystemName is empty go to GetSystemName
    end
    
ContinueAfterName:
    if property `calendar` of Map is `on` set style `display` of CalendarIcon to `block`
    else set style `display` of CalendarIcon to `none`
    set the content of Date to the day number

	! Show the system
    set the content of SystemNamePanel to SystemName
    on click ProfilesButton go to DoProfiles

	! Get the current sensor values

	attach VersionNumber to `systemversion`
    if not Mobile set style `color` of VersionNumber to `black`
!    set the content of VersionNumber to `v:`
    attach StatusFlag to `statusflag`
    
!   log Map
    put property `profiles` of Map into Profiles
	put property `profile` of Map into CurrentProfile
    if CurrentProfile is empty put 0 into CurrentProfile
    ! If the calendar is on, resolve the profile for today
    if property `calendar` of Map is `on`
    begin
        put property `calendar-data` of Map into Value
        if Value is not empty
        begin
            put the day into N
            add 6 to N
            put N modulo 7 into N
            put element N of Value into Value
            if Value is not empty
            begin
                put property `day` cat N cat `-profile` of Value into Value
                if Value is not empty
                begin
                    put the json count of Profiles into R
                    put 0 into N
                    while N is less than R
                    begin
                        put element N of Profiles into Profile
                        if property `name` of Profile is Value put N into CurrentProfile
                        add 1 to N
                    end
                end
            end
        end
    end
    set property `profile` of Map to CurrentProfile
    if Profiles is empty put `{}` into Profile else put element CurrentProfile of Profiles into Profile
    put property `name` of Profile into Name
    set the text of ProfilesButton to `Profile: ` cat Name
    put property `rooms` of Profile into Rooms

    put the json count of Rooms into R
    if R is RoomCount clear Redraw
    else
    begin
    	put R into RoomCount
        set Redraw
    end
    if Redraw
    begin
    	clear MainPanel
    	set Refresh
    end
!    wait 2 seconds
!    log `Start the redraw`

    set the elements of Mode to RoomCount
    set the elements of ModeHolder to RoomCount
    set the elements of ModeButton to RoomCount
    set the elements of RoomSpec to RoomCount
    set the elements of RoomNamePanel to RoomCount
    set the elements of RoomTempPanel to RoomCount
    set the elements of RoomToolsButton to RoomCount
    set the elements of RoomStatusButton to RoomCount
    set the elements of RoomStatus to RoomCount
    set the elements of RelayState to RoomCount
    set the elements of ModeHolder to RoomCount
    set the elements of ModeButton to RoomCount
    set the elements of ModeIcon to RoomCount
    set the elements of ModeText to RoomCount
    set the elements of Snowflake to RoomCount

    gosub to UpdateRooms

!	Get the system status
	put 0 into NGood
    put 0 into NBad
    put 0 into RoomIndex
    while RoomIndex is less than RoomCount
    begin
    	index RoomStatus to RoomIndex
        if RoomStatus is `good` add 1 to NGood
        else if RoomStatus is `fail` add 1 to NBad
    	add 1 to RoomIndex
    end
    if NGood is RoomCount
    begin
        set style `background` of StatusFlag to `lightgreen`
        set style `border` of StatusFlag to `1px solid green`
    end
    else if NBad is RoomCount
    begin
        set style `background` of StatusFlag to `red`
        set style `border` of StatusFlag to `1px solid lightred`
    end
    else
    begin
        set style `background` of StatusFlag to `gold`
        set style `border` of StatusFlag to `1px brown`
    end
    
    on click RoomTempPanel
    begin
    	put the index of RoomTempPanel into N
!       Restore any previously shown battery display
        gosub to RestoreAllTemps
!       Show battery for the clicked room
        index RoomTempPanel to N
		put element N of Rooms into RoomSpec
        put `` cat property `sensor` of RoomSpec into SensorIP
        if SensorIP is not empty
        begin
            put property `battery` of RoomSpec into Battery
            if Battery is greater than 40 put `lightgreen` into Color
            else if Battery is greater than 25 put `orange` into Color
            else put `deeppink` into Color
        	set style `color` of RoomTempPanel to Color
        	set the content of RoomTempPanel to Battery cat `%`
        end
    end
    
!    put property `status` of Sensors into SystemStatus

    put StaticData into storage as `StaticData`

    clear Refresh
    clear Redraw
    clear Blocked

    set style `background` of Alive to `#fee`
    wait 50 ticks
    set style `background` of Alive to `#228`
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Update all the rooms
UpdateRooms:
! 	Draw a row for each room
    put 0 into RoomIndex
    while RoomIndex is less than RoomCount
    begin
        index Mode to RoomIndex
        index ModeHolder to RoomIndex
        index ModeButton to RoomIndex
        index ModeIcon to RoomIndex
        index RoomSpec to RoomIndex
        index RelayState to RoomIndex
        index RoomNamePanel to RoomIndex
        index RoomTempPanel to RoomIndex
        index RoomToolsButton to RoomIndex
        index RoomStatusButton to RoomIndex
        index RoomStatus to RoomIndex
        index ModeText to RoomIndex
        index Snowflake to RoomIndex

        put property `room-` cat RoomIndex of StaticData into RoomData
        if RoomData is empty
        begin
        	put `{}` into RoomData
            set property `alive` of RoomData to `true`
        end

        if Redraw
        begin
            ! Render the Webson spec for a room
            if RoomWebson is empty
                rest get RoomWebson from `resources/webson/room.json?v=` cat now
            		or go to HandleInternalError
        	put RoomWebson into Webson
        	replace `/ROOM/` with RoomIndex in Webson
        	render Webson in MainPanel

		    ! Attach to various elements of the display
            attach ModeHolder to `room-` cat RoomIndex cat `-mode-holder` or
                go to NextRoom
            attach RoomNamePanel to `room-name-` cat RoomIndex or
                go to NextRoom
		    attach RoomTempPanel to `room-temp-` cat RoomIndex or
                go to NextRoom
            attach RoomToolsButton to `room-tools-` cat RoomIndex or
                go to NextRoom
            attach RoomStatusButton to `room-status-` cat RoomIndex or
                go to NextRoom
            attach Snowflake to `room-snowflake-` cat RoomIndex or
                go to NextRoom
        end

		! Set the room name
		put element RoomIndex of Rooms into RoomSpec
        put property `name` of RoomSpec into RoomName
        set the content of RoomNamePanel to RoomName
        
        ! Get the mode
        put property `mode` of RoomSpec into Mode
        if Mode is empty put `off` into Mode
        
        ! Show the current temperature and relay state
!        log RoomSpec
        put property `sensor` of RoomSpec into SensorIP
        put property `relayType` of RoomSpec into RelayType
        put property `relay` of RoomSpec into RelayState
        put property `temperature` of RoomSpec into Temperature
    	put property `battery` of RoomSpec into Battery
        put property `timestamp` of RoomSpec into Timestamp
        put property `advance` of RoomSpec into Advance
        put property `status` of RoomSpec into RoomStatus
        if RelayType is `Manual`
        begin
            set the content of RoomTempPanel to `Manual`
            if Mode is `on` set style `background` of RoomTempPanel to `red`
            else if Mode is `boost` set style `background` of RoomTempPanel to `red`
            else set style `background` of RoomTempPanel to `blue`
        end
        else if SensorIP is not empty
        begin
            put the timestamp into Now
            if Timestamp is not empty
            begin
            	take Timestamp from Now giving Elapsed
!      log `Elapsed: ` cat Elapsed
				if Elapsed is greater than 3660
                begin
                	if property `alive` of RoomData is `true`
                    begin
!                    	put `The sensor for ` cat RoomName cat ` is not reporting. ` into SystemStatus
!                    	alert `The sensor for ` cat RoomName cat ` has not reported recently. `
!                        	cat `If it doesn't come back by itself, power it down then re-power it.`
                    	set property `alive` of RoomData to `false`
                    end
                end
                else set property `alive` of RoomData to `true`
            end
            set property `room-` cat RoomIndex of StaticData to RoomData
            if property `relays` of RoomSpec is empty put `true` into IsAlive
!            else if property `linked` of RoomSpec is `no` put `true` into IsAlive
            else put property `alive` of RoomData into IsAlive
            put `true` into IsAlive
            if IsAlive is `true`
            begin
            	set style `color` of RoomTempPanel to `white`
                if Temperature is 0 set the content of RoomTempPanel to empty 
                else
                begin
                    put `` cat Temperature modulo 100 into T
                    divide Temperature by 100
                    put `` cat Temperature cat `.` cat left 1 of T into Temperature
                end
                set the content of RoomTempPanel to Temperature cat `&deg;C`
            	if RelayState is not `off` set style `background` of RoomTempPanel to `red`
            	else set style `background` of RoomTempPanel to `blue`
            end
            else
            begin
        		set the content of RoomTempPanel to `--.-&deg;C`
                set style `background` of RoomTempPanel to `blue`
            end
        end

		! Deal with the Protect flag
        set style `display` of Snowflake to `none`
        if SensorIP is not empty
        begin
!			if property `protect` of Sensors is SensorIP
!        	begin
!        		set style `display` of Snowflake to `block`
!            end
        end

		if RoomStatus is `good`
        begin
            set style `background` of RoomStatusButton to `lightgreen`
            set style `border` of RoomStatusButton to `1px solid green`
        end
        else if RoomStatus is `fail`
        begin
            set style `background` of RoomStatusButton to `red`
            set style `border` of RoomStatusButton to `1px solid darkred`
        end
        else
        begin
            set style `background` of RoomStatusButton to `gold`
            set style `border` of RoomStatusButton to `1px solid brown`
        end

        ! Show the mode indicator
        put property `relays` of RoomSpec into Relays
        put the json count of Relays into NR
        if NR is 1
        	if element 0 of Relays is empty put 0 into NR
        if NR is 0
        begin
            clear ModeHolder
            if NoneWebson is empty
            rest get NoneWebson from `resources/webson/none.json?v=` cat now
            	or go to HandleInternalError
            put NoneWebson into Webson
            replace `/ROOM/` with RoomIndex in Webson
            render Webson in ModeHolder
        end
        else
        begin
            clear ModeHolder
        	if Mode is `timed`
            begin
                if TimedWebson is empty
                	rest get TimedWebson from `resources/webson/timed.json?v=` cat now
                		or go to HandleInternalError
                put TimedWebson into Webson
            end
            else if Mode is `boost`
            begin
                if BoostWebson is empty
                	rest get BoostWebson from `resources/webson/boost.json?v=` cat now
                		or go to HandleInternalError
                put BoostWebson into Webson
            end
            else if Mode is `on`
            begin
                if OnWebson is empty
                	rest get OnWebson from `resources/webson/on.json?v=` cat now
                		or go to HandleInternalError
                put OnWebson into Webson
            end
            else if Mode is `off`
            begin
                if OffWebson is empty
                	rest get OffWebson from `resources/webson/off.json?v=` cat now
                		or go to HandleInternalError
                put OffWebson into Webson
            end
            replace `/ROOM/` with RoomIndex in Webson
            render Webson in ModeHolder
        	attach ModeIcon to `room-` cat RoomIndex cat `-mode-icon` or goto UR2
    	    attach ModeText to `room-` cat RoomIndex cat `-mode-text` or goto UR2
	        attach ModeInfo to `room-` cat RoomIndex cat `-mode-info` or goto UR2
        UR2:
        	if Mode is `timed`
            begin
                if RoomStatus is `good`
                begin
                	put `` cat Advance into Advance
                    if Advance is not empty
                    begin
                        if Advance is `-`
                        begin
                	       	set attribute `src` of ModeIcon to `resources/icon/clock.png`
                         	set the content of ModeText to `Timed`
                            set style `font-size` of ModeText to `1.2em`
                        end
                        else
                        begin
                            if Advance is not `C`
                            begin
                        		set attribute `src` of ModeIcon to `resources/icon/advance.png?v=12345`
                                set the content of ModeText to `Advance`
                              	set style `font-size` of ModeText to `1.0em`
                            end
                        end
                    end
                end

                put property `events` of RoomSpec into Events
                divide now by 60 giving N
                put N modulo 24*60 into N
                divide N by 60 giving H
                put N modulo 60 into M
                put 0 into E
                while E is less than the json count of Events
                begin
                    put element E of Events into Event
                    put property `until` of Event into UntilTime
                    put property `temp` of Event into UntilTemp
                    split UntilTime on `:` giving Finish
                    
                    if Advance is not `-`
                    begin
                    	add 1 to E giving F
                        if F is not less than the json count of Events put 0 into F
                        put element F of Events into Event2
                        put property `until` of Event2 into UntilTime
                    	put property `temp` of Event2 into UntilTemp
                    end
                    index Finish to 0
                    put the value of Finish into FH
                    if FH is 0 put 24 into FH
                    if H is less than FH
                    begin
                        set the content of ModeInfo to UntilTemp
                            cat `&deg;C->` cat UntilTime
                        go to HandleClicks
                    end
                    else if H is FH
                    begin
                        index Finish to 1
                        put the value of Finish into FM
                        if M is less than FM
                        begin
                            set the content of ModeInfo to UntilTemp
                                cat `&deg;C->` cat UntilTime
                            go to HandleClicks
                        end
                    end
                    add 1 to E
                end
                put element 0 of Events into Event
                put property `until` of Event into Finish
                put property `temp` of Event into Temperature
                if property `linked` of RoomSpec is `yes`
                	set the content of ModeInfo to Temperature cat `&deg;C->` cat Finish
                else set the content of ModeInfo to `->` cat Finish
            end
            else if Mode is `boost`
            begin
                attach BoostName to `room-` cat RoomIndex cat `-mode-info`
                put property `until` of RoomSpec into Boost
                if Boost is not empty
                begin
                    take the timestamp from Boost
                    divide Boost by 60000
                    add 1 to Boost
                    if Boost is 1 set the content of BoostName to Boost cat ` min`
                    else set the content of BoostName to Boost cat ` mins`
                end
            end
            else if Mode is `on`
            begin
                attach TargetTemp to `room-` cat RoomIndex cat `-mode-info`
                put empty into TVal
                if property `sensor` of RoomSpec is not empty
                begin
                	if property `linked` of RoomSpec is `yes`
                		put property `target` of RoomSpec cat `&deg;C` into TVal
                end
                set the content of TargetTemp to TVal
            end
            else if Mode is `off`
            begin
            end
		end

	HandleClicks:
		! Handle a click on the row hamburger
        on click RoomToolsButton
        begin
        	if Blocked stop
        	put the index of RoomToolsButton into ClickIndex
            go to RoomTools
        end

	    ! Handle a click on a mode button
        if the json count of Relays is not 0
        begin
            attach ModeButton to `room-` cat RoomIndex cat `-mode-button`
            on click ModeButton
            begin
                if Blocked stop
                set Blocked
                gosub to MaskScreen
!                on click ProfilesButton begin end
                put the index of ModeButton into ClickIndex
                if ModeScript is empty
                    rest get ModeScript from `resources/as/mode.as?v=` cat now
            			or go to HandleInternalError
    			put `{}` into Result
                run ModeScript with MainPanel
                    and ModePanel
                    and ModeButton
                    and Mode
                    and Map
                    and ClickIndex
                    and Result
                if property `Action` of Result is empty
                begin
                    gosub to Unmask
                    clear Blocked
                    set Redraw
                    go to RedrawFromMap
                end
                put `refresh` into Prompt
                gosub to Unmask
                set Redraw
                go to ProcessResult
            end
        end
    NextRoom:
        add 1 to RoomIndex
    end
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Reset the MAC address and password
Reset:
	put empty into storage as `rbr-mac`
    put empty into storage as `password`
    clear Blocked
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Deal with the main hamburger menu
ShowMenu:
	set Blocked
    gosub to MaskMainPanel
    wait 20 ticks
	clear MainPanel
    if MainMenuWebson is empty
        rest get MainMenuWebson from `resources/webson/mainmenu.json?v=` cat now
            or go to HandleInternalError
    render MainMenuWebson in MainPanel
    attach GetSystemNameButton to `button-getname`
    attach GetRequestButton to `button-getrequest`
    attach AddButton to `button-add`
    attach CancelButton to `button-cancel`

    on click GetSystemNameButton
    begin
    	set Flag
        go to GetSystemName
    end

    on click GetRequestButton
    begin
    	set Flag
        go to GetRequestRelay
    end

    on click AddButton
    begin
        gosub to MaskScreen
        put `{}` into RequestData
        rest get Value from `resources/json/newroomspec.json?v=` cat now
            or go to HandleInternalError
        set property `action` of RequestData to `addroom`
        set property `spec` of RequestData to Value
        fork to PostAndConfirm
        if Rooms is empty put json `[]` into Rooms
        append Value to Rooms
        gosub to CopyRoomsToMap
    	clear MainPanel
        set Redraw
        clear Blocked
        stop
    end

    on click CancelButton
    begin
    	clear MainPanel
        clear Blocked
        put `first` into Prompt
        set Redraw
        stop
    end

	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Get the name of the system
GetSystemName:
	set Blocked
    clear MainPanel
    put property `name` of Map into SystemName
    if SystemName is `undefined` put empty into SystemName
!   Standard input form
    if GetNameWebson is empty
        rest get GetNameWebson from `resources/webson/getname.json?v=` cat now
            or go to HandleInternalError
    render GetNameWebson in MainPanel
    attach Input to `getname-input`
    attach OKButton to `getname-ok`
    attach CancelButton to `getname-cancel`
    attach KeyboardButton to `getname-keyboard`
    if Flag set the content of Input to SystemName
    else set style `display` of CancelButton to `none`
    on click KeyboardButton
    begin
        put the content of Input into SystemName
        clear MainPanel
        go to GetSystemNameKeyboard
    end
    on click OKButton
    begin
    	clear MainPanel
        clear Blocked
        set Redraw
        set property `name` of Map to the content of Input
        put the content of Input into storage as `SystemName`
        put `{}` into RequestData
        set property `action` of RequestData to `name`
        set property `name` of RequestData to the content of Input
        go to PostRequest
    end
    on click CancelButton
    begin
    	clear MainPanel
        clear Blocked
        set Redraw
        stop
    end
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Get the system name using the popup keyboard
GetSystemNameKeyboard:
    put `{}` into Result
    set property `title` of Result to `System name`
    set property `text` of Result to SystemName
    rest get Script from `resources/as/keyboard.as?v=` cat now
        or go to HandleInternalError
    run Script with MainPanel and Result
    clear Blocked
    put `first` into Prompt
    set Redraw
    if property `cancelled` of Result is `true` stop
    put property `text` of Result into SystemName
    set property `name` of Map to SystemName
    put SystemName into storage as `SystemName`
    put `{}` into RequestData
    set property `action` of RequestData to `name`
    set property `name` of RequestData to SystemName
    go to PostRequest

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Get the name of the system request relay
GetRequestRelay:
	set Blocked
    clear MainPanel
    if GetRequestWebson is empty
        rest get GetRequestWebson from `resources/webson/getrequest.json?v=` cat now
            or go to HandleInternalError
    render GetRequestWebson in MainPanel
    attach Input to `getrequest-input`
    attach OKButton to `getrequest-ok`
    attach CancelButton to `getrequest-cancel`
    attach KeyboardButton to `getrequest-keyboard`
    put property `request` of Map into RequestIP
    if RequestIP is `undefined` put empty into RequestIP
    if Flag set the content of Input to RequestIP
    else set style `display` of CancelButton to `none`
    on click KeyboardButton
    begin
        put the content of Input into RequestIP
        clear MainPanel
        go to GetRequestRelayKeyboard
    end
    on click OKButton
    begin
    	clear MainPanel
        clear Blocked
        set Redraw
        put `{}` into RequestData
        set property `action` of RequestData to `request`
        set property `request` of RequestData to the content of Input
        go to PostRequest
    end
    on click CancelButton
    begin
    	clear MainPanel
        clear Blocked
        set Redraw
        stop
    end
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Get the request relay name using the popup keyboard
GetRequestRelayKeyboard:
    put `{}` into Result
    set property `title` of Result to `Request relay name`
    set property `text` of Result to RequestIP
    rest get Script from `resources/as/keyboard.as?v=` cat now
        or go to HandleInternalError
    run Script with MainPanel and Result
    clear Blocked
    put `first` into Prompt
    set Redraw
    if property `cancelled` of Result is `true` stop
    put `{}` into RequestData
    set property `action` of RequestData to `request`
    set property `request` of RequestData to property `text` of Result
    go to PostRequest

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Copy the current room set to the map
CopyRoomsToMap:
    if Map is empty gosub to CreateDefaultMap
    if CurrentProfile is empty put 0 into CurrentProfile
    put property `profiles` of Map into Profiles
    put element CurrentProfile of Profiles into Profile
    set property `rooms` of Profile to Rooms
    set element CurrentProfile of Profiles to Profile
    set property `profiles` of Map to Profiles
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Deal with profiles
DoProfiles:
	if ProfileModule is running stop
                if Blocked stop
                set Blocked
!                gosub to MaskScreen
!	set Blocked
    gosub to MaskMainPanel
    put `{}` into Result
    rest get Script from `resources/as/profiles.as?v=` cat now
    run Script with MainPanel and Map and Result as ProfileModule
    put `first` into Prompt
    gosub to Unmask
    set Redraw
    go to ProcessResult

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Create a default map
CreateDefaultMap:
    log `No map available; creating template`
    put json `{"profiles":[{"name":"Default","rooms":[]}],"profile":0,"calendar":"off","calendar-data":[],"name":"New System"}` into Map
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	The room tools
RoomTools:
	set Blocked
    gosub to MaskScreen
    wait 20 ticks ! to allow things to complete before running the editor!
	clear MainPanel
    if RoomToolsMenuWebson is empty
        rest get RoomToolsMenuWebson from `resources/webson/roomtoolsmenu.json?v=` cat now
            or go to HandleInternalError
    render RoomToolsMenuWebson in MainPanel
    gosub to Unmask
    put element ClickIndex of Rooms into RoomSpec
    put property `name` of RoomSpec into Name
!    put property Name of Sensors into RoomSpec
    put `{}` into Result
    rest get Script from `resources/as/roomtools.as?v=` cat now
    run Script with MainPanel and Map and RoomSpec and ClickIndex and Result
    go to ProcessResult

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Show a help page
RunHelp:
	if HelpScript is empty stop
	set Blocked
    gosub to Unmask
    set style `display` of OuterPanel to `none`
    set style `display` of HelpPanel to `block`
    run HelpScript with HelpPanel and SID and TID as Storyteller
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Run the statistics module
Statistics:
	set Blocked
    set style `display` of OuterPanel to `none`
    set style `display` of StatisticsPanel to `block`
    rest get Script from `resources/as/statistics.as?v=` cat now
        or go to HandleInternalError
    run Script with StatisticsPanel and Map
    log `Statistics finished`
    set style `display` of OuterPanel to `block`
    set style `display` of StatisticsPanel to `none`
    clear MainPanel
    clear Blocked
    set Redraw
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Validate the map has essential fields.
!   If any are missing (e.g. MQTT truncation), restore from backup.
ValidateMap:
    if property `name` of Map is empty go to RestoreMapBackup
    if property `profiles` of Map is empty go to RestoreMapBackup
    ! Map looks complete; save as backup
    put Map into storage as `map-backup`
    return

RestoreMapBackup:
    get Value from storage as `map-backup`
    if Value is not empty
    begin
        log `Incomplete map received; restoring from backup`
        put Value into Map
    end
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Mask the screen
MaskScreen:
	set style `display` of Mask to `block`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Mask the main panel
MaskMainPanel:
	set style `display` of BannerMask to `block`
    set style `display` of TitleMask to `block`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Unmask everything
Unmask:
	set style `display` of Mask to `none`
	set style `display` of BannerMask to `none`
    set style `display` of TitleMask to `none`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Restore all room temperature displays (cancel any battery view)
RestoreAllTemps:
    put 0 into R
    while R is less than RoomCount
    begin
        index RoomTempPanel to R
        put element R of Rooms into RoomSpec
        put property `temperature` of RoomSpec into Temperature
        put property `relay` of RoomSpec into RelayState
        put property `relayType` of RoomSpec into RelayType
        if RelayType is `Manual`
        begin
            set the content of RoomTempPanel to `Manual`
            if RelayState is not `off` set style `background` of RoomTempPanel to `red`
            else set style `background` of RoomTempPanel to `blue`
        end
        else
        begin
            set style `color` of RoomTempPanel to `white`
            put `` cat Temperature modulo 100 into T
            divide Temperature by 100
            put `` cat Temperature cat `.` cat left 1 of T into Temperature
            set the content of RoomTempPanel to Temperature cat `&deg;C`
            if RelayState is not `off` set style `background` of RoomTempPanel to `red`
            else set style `background` of RoomTempPanel to `blue`
        end
        add 1 to R
    end
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Process the result of running another module
ProcessResult:
!    log `Result: ` cat Result
    set Blocked
    gosub to MaskScreen
    gosub to ApplyLocalResult
    gosub to SendUIRequest
    put property `request` of Result into Request
    if Request is `Help`
    begin
        put property `data` of Result into RequestData
        split RequestData on ` ` giving Result
        index Result to 0
        put Result into SID
        index Result to 1
        put Result into TID
        go to RunHelp
    end
    if Request is `Update`
    begin
        put property `data` of Result into RequestData
        put property `action` of RequestData into Value
        ! Get the current rooms from the map
        put property `profiles` of Map into Profiles
        put element CurrentProfile of Profiles into Profile
        put property `rooms` of Profile into Rooms
        if Value is `rooms`
            put property `rooms` of RequestData into Rooms
        else if Value is `roomname`
        begin
            put element ClickIndex of Rooms into RoomSpec
            set property `name` of RoomSpec to property `name` of RequestData
            set element ClickIndex of Rooms to RoomSpec
        end
        else if Value is `roomdata`
        begin
            put element ClickIndex of Rooms into RoomSpec
            put property `items` of RequestData into Value
            set property `sensor` of RoomSpec to property `sensor` of Value
            set property `relays` of RoomSpec to property `relays` of Value
            set property `relayType` of RoomSpec to property `relayType` of Value
            set property `linked` of RoomSpec to property `linked` of Value
            set property `protect` of RoomSpec to property `protect` of Value
            set property `ptemp` of RoomSpec to property `ptemp` of Value
            set property `p100Email` of RoomSpec to property `p100Email` of Value
            set property `p100Password` of RoomSpec to property `p100Password` of Value
            set element ClickIndex of Rooms to RoomSpec
        end
        gosub to CopyRoomsToMap
        ! Normalise to `rooms` action so the controller handles it
        put `{}` into RequestData
        set property `action` of RequestData to `rooms`
        set property `rooms` of RequestData to Rooms
        gosub to SendRoomsUpdate
    end
    clear MainPanel
    set Redraw
    put `first` into Prompt
    wait 10 ticks
    clear Blocked
    go to MainProcessingTask

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Send a request to the system controller
SendUIRequest:
    if property `Action` of Result is empty return
    log `Sending UI request to ServerTopic: ` cat Result
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message Result
        giving SendOK
    if not SendOK
    begin
        log `WARNING: MQTT send failed (no broker acknowledgment)`
        alert `Request failed - please retry`
        put `first` into Prompt
    end
    else log `MQTT OK`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Send RequestData to the controller and return
SendRoomsUpdate:
!    log `Sending rooms update to ServerTopic: ` cat RequestData
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message RequestData
        giving SendOK
    if not SendOK
    begin
        log `WARNING: MQTT send failed (no broker acknowledgment)`
        alert `Request failed - please retry`
        put `first` into Prompt
    end
    else log `MQTT OK`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Post RequestData to the controller and stop
PostAndConfirm:
PostRequest:
    log `Posting request to ServerTopic: ` cat RequestData
    send to ServerTopic
        sender MyTopic
        action `uirequest`
        message RequestData
        giving SendOK
    if not SendOK
    begin
        log `WARNING: MQTT send failed (no broker acknowledgment)`
        alert `Request failed - please retry`
        put `first` into Prompt
    end
    else log `MQTT OK`
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Apply a UI action to the local cached map immediately.
!   This avoids reopening a dialog from stale map data while the controller
!   update is still in flight.
ApplyLocalResult:
    if property `Action` of Result is `Update Profiles`
    begin
        put property `profiles` of Result into Value
        if Value is not empty set property `profiles` of Map to Value
        put property `profile` of Result into Value
        if Value is not empty set property `profile` of Map to Value
        put property `calendar` of Result into Value
        if Value is not empty set property `calendar` of Map to Value
        put property `calendar-data` of Result into Value
        if Value is not empty set property `calendar-data` of Map to Value
        return
    end
    if property `Action` of Result is not `Operating Mode` return
    put property `profiles` of Map into Profiles
    if Profiles is empty return
    put property `profile` of Map into CurrentProfile
    if CurrentProfile is empty put 0 into CurrentProfile
    put element CurrentProfile of Profiles into Profile
    put property `rooms` of Profile into Rooms
    if ClickIndex is not numeric return
    if ClickIndex is less than 0 return
    put the json count of Rooms into N
    if ClickIndex is not less than N return
    put element ClickIndex of Rooms into RoomSpec
    if RoomSpec is empty return
    set property `mode` of RoomSpec to property `Mode` of Result
    put property `advance` of Result into Value
    if Value is `A` set property `advance` of RoomSpec to Value
    else if Value is `C` set property `advance` of RoomSpec to Value
    else if Value is `-` set property `advance` of RoomSpec to `-`
    if property `Mode` of Result is `on`
        set property `target` of RoomSpec to property `target` of Result
    else if property `Mode` of Result is `boost`
    begin
        ! Save the previous mode so Cancel Boost can restore it
        put property `mode` of RoomSpec into Value
        if Value is not `boost`
            set property `prevmode` of RoomSpec to Value
        put property `target` of Result into Value
        if Value is not empty
            if Value is not `undefined`
                set property `target` of RoomSpec to Value
        put property `boost` of Result into Value
        if Value is not empty
            if Value is not `undefined`
                set property `boost` of RoomSpec to Value
    end
    set element ClickIndex of Rooms to RoomSpec
    gosub to CopyRoomsToMap
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Flash the hourglass while waiting
FlashHourglass:
    set Waiting
    set Flashing
    put 0 into Flashes
	while Waiting
    begin
    	set style `display` of Hourglass to `block`
    	wait 50 ticks
        set style `display` of Hourglass to `none`
        wait 50 ticks
        add 1 to Flashes
        if Flashes is greater than 99 go to FH2
    end
FH2:
    clear Flashing
    clear Waiting
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Handle an error in calling up a module
HandleInternalError:
	alert `An internal error occurred. Please refresh the page.`
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Warn the user and abandon this run
AbandonShip:
	alert `An error has occurred while communicating with the controller.`
    	cat newline cat `Please refresh this browser page to restart.`
    exit
