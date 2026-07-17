!! Room By Room — new UI shell. The single script that boots the mobile webapp, opens an MQTT WebSocket to the controller, ingests its map, renders the home screen, and routes every user gesture into a `uirequest` reply.
!!
!! Architecture in brief. The shell is a long-running message loop: MQTT connect → first map → render → 10-second polling refresh. The controller is authoritative for relay/schedule/temperature state; the UI mirrors it optimistically (mutating its local copy on user action, shipping a `uirequest`, and reconciling on the next map push). All sheet UIs follow the same pattern — snapshot live data into Editing* working copies on open, mutate locally, ship one `Update Profiles` (or `Update Rooms`) on Save, discard on Cancel.
!!
!! Resilience layers. MQTT WebSockets are silently torn down by mobile OSes when the tab is backgrounded; we paper over that with a tab-resume hook (reload if stale >5min, otherwise refresh), a 30-second first-map watchdog (capped at 3 attempts), and a poll-interval staleness check (reload if no reply for 60s). A demo mode kicks in when there are no credentials, rendering a baked map and the About sheet for marketing visits.
!!
!! Slice history (preserved for archaeology): 02 TopBar + 03 RoomRow + 04 SummaryCard + 05 Sheet chrome + MenuSheet + 06 ProfileSheet + 07 RoomRow expansion (mode/target/boost/edit-schedule) + 08 Time-of-day background gradient. Subsequent slices added Schedule editor, Device editor, System sheet, Outside sheet, Info sheet, About sheet.
!!
!! The script opens with all DOM-element handle declarations (one block per sheet or feature), then the script-level state variables grouped by concern, and finally the synchronous bootstrap that wires the topbar, fetches credentials, opens MQTT, and arms the message loop. Everything past `stop` (line ~702) is reached only via the message handler or click handlers.

	script Shell

	div AppRoot
	div TopBarHolder
	div MainHolder
	div SystemId
	button HeartbeatBtn
	div HeartbeatDot
	button HouseMark
	div AboutSheetEl
	button AboutTabAbout
	button AboutTabManual
	div AboutBodyAbout
	div AboutBodyManual
	button AboutCtaSetup
	div RoomName
	div HeatingTag
	div OfflineTag
	div Subline
	div TempEl
	div Setpoint
	div Chip
	div ChipIcon
	div SummaryTitle
	div SummarySubtitle
	div SummaryChip
	div SummaryChipIcon
	div SummaryDot
	div SummaryAvg
	div SummaryOutside
	div SummaryToday
	div SummaryProfileName
	button MenuButton
	button ProfilePill
	div SheetRoot
	div SheetScrim
	div SheetContainer
	button SheetCloseBtn
	div SheetTitleEl
	div SheetContent
	div MenuSheetEl
	button MenuRowSystem
	button MenuRowDevices
	button MenuRowOutside
	button MenuRowHelp
!	Owned by the profile-sheet module — declared here so HideAllSheets can
!	hide it. The module attaches it independently for its own toggling.
	div ProfileSheetEl
!	Owned by the schedule-editor module — declared here so HideAllSheets
!	can hide it. Each script gets its own DOM handle to the same element
!	via attach-by-id.
	div ScheduleSheetEl
!	Owned by the device-editor module — declared here so HideAllSheets can
!	hide it (same attach-by-id pattern as ScheduleSheetEl).
	div DeviceEditorSheetEl
	div SystemSheetEl
	input SystemSheetName
	button SystemSheetTypeBoiler
	button SystemSheetTypeHeatPump
	button SystemSheetSaveBtn
	button SystemSheetCancelBtn
	div OutsideSheetEl
	input OutsideSheetSensor
	input OutsideSheetFrost
	button OutsideSheetSaveBtn
	button OutsideSheetCancelBtn
	div SummaryOutsideFrost
	div InfoSheetEl
	div InfoRelayValue
	div InfoTempValue
	div InfoHumidityValue
	div InfoBatteryValue
	div InfoAgeValue

!	Per-row interactive elements (indexed via `index X to RoomIndex` in the
!	render loop so each click handler can recover its row via `the index of X`).
	button RestRow
	button InfoBtn
	div ExpansionEl
	button ModeTimedBtn
	button ModeBoostBtn
	button ModeOnBtn
	button ModeOffBtn
	div TargetBlockEl
	div TargetValueEl
	button TargetMinusBtn
	button TargetPlusBtn
	div BoostBlockEl
	button BoostOffBtn
	button Boost30Btn
	button Boost1hBtn
	button Boost2hBtn
	div AdvanceBlockEl
	button AdvanceBtn
	button EditScheduleBtn

	variable LayoutWebson
	variable TopBarWebson
	variable SummaryWebson
	variable SheetWebson
	variable MenuWebson
	variable RoomRowText
	variable RoomsList
	variable Room
	variable RoomIndex
	variable RoomCount
	variable RowText
	variable IndexStr
	variable Mode
	variable TempVal
	variable TargetTemp
	variable NextTime
	variable NextTarget
	variable NextPrefix
	variable Offline
	variable Sensor
	variable BoostVal
	variable NameText
	variable SublineText
	variable CallingForHeat
	variable ChipBg
	variable ChipFg
	variable ChipIconUrl
	variable MaskCss

!	Summary pass variables.
	variable LoopI
	variable CurRoom
	variable RName
	variable Ttemp
	variable Tsensor
	variable Toffline
	variable Tcalling
	variable HeatingCount
	variable HeatingNames
	variable SumTenths
	variable AvgCount
	variable TenthsOne
	variable DotIdx
	variable DecPart
	variable OutsideTemp
	variable AvgText
	variable AvgInt
	variable AvgDec
	variable OutsideText
	variable TitleText
	variable SubtitleText
	variable ProfileName

!	Expansion / interaction state.
	variable ExpandedIndex
	variable ClickIndex
	variable NewMode
	variable Tmode
	variable Ttarget
	variable BoostDur
	variable Advance
	variable AdvanceNextTime
	variable PrevMode
!	Boost-panel state. BoostPanelOpenIndex == ClickIndex while the user is
!	configuring a Boost from a non-Boost mode (duration buttons visible, no
!	duration committed yet). Cleared on commit, on Off-button cancel, on
!	mode change, or when the expansion is closed. The target tile during
!	configuring shows Room.target directly — Boost and On share a single
!	target, so any +/- edit while the panel is open is a real commit to
!	Room.target (same path as in On mode), not a staged working copy.
	variable BoostPanelOpenIndex
	variable BoostState
	variable TargetVis
	variable PanelWasOpen
!	Scratch state for SyncCurrentRoomToMap (and the boost-until inline
!	updates in ApplyBoost / BoostOffTapped). Keeps Map.profiles in step with
!	RoomsList after each per-room toggle so a subsequent Save that ships
!	`Update Profiles` doesn't revert the change.
	variable SyncProfiles
	variable SyncProfile
	variable SyncRooms
	variable SyncLegacyRoom
	variable SyncLegacyIdx
	variable SyncUiMode
	variable SyncBaseMode
	variable SyncBoostUntil
	variable SyncPrevModeLegacy
	variable TempStr
	variable TempTenths
	variable TempT
	variable TargetT
	variable Diff
	variable NewCalling

!	Time-of-day background.
	variable Hour
	variable LastHour
	variable GTop
	variable GMid
	variable GBot
	variable BgValue
	variable Glow

!	MQTT connection state.
	variable Credentials
	variable Broker
	variable Port
	variable Username
	variable Password
	variable MAC
	variable MyID
	topic ServerTopic
	topic MyTopic
	variable ReceivedMessage
	variable Prompt
	variable FirstMapDone
	variable SheetsReady
	variable LastReceivedAt
	variable ResumeAge
	variable ConsecutiveSendFailures
	variable FirstMapAttempts
	variable HeartbeatCount

!	Map ingestion / transformation state.
	variable Map
	variable MapResult
	module MapToRoomsModule
!	Scratch source-text holder for `rest get ModuleSrc ... ; run ModuleSrc as Module`.
!	Re-used for every sub-module load.
	variable ModuleSrc
	variable Profiles
	variable CurrentProfile
	variable ActiveProfile
	variable ActiveProfileName
	variable SystemName

!	Date-formatting lookup tables and scratch.
	variable DayNames
	variable MonthNames
	variable DayName
	variable MonthName
	variable DateD
	variable DateDN
	variable DateM

!	Outbound (uirequest) payload state.
	variable Result
	variable SendOK
	variable ModeForServer
	variable BoostMinutes
	variable RoomNameForServer
	variable TargetForServer
	variable CalendarOn
	variable DemoMode
!	SendUpdateProfiles inputs — set by callers, read by the helper.
	variable PayloadProfiles
	variable PayloadActiveProfileIdx
	variable PayloadCalendarOnFlag
	variable PayloadCalendarData
	variable AboutSheetWebson

!	Profile sheet reply-state. The sheet itself lives in profile-sheet.as;
!	we ship an open-message and park on the reply (cancelled / profiles /
!	activeIdx / calendarOn / calendarData).
	module ProfileSheetModule
	variable ProfileResult
!	Cross-routine scratch for confirm-dialog responses (still used by
!	ResetCredentialsAndReload).
	variable ConfirmFlag

!	Schedule editor reply-state. The editor itself lives in schedule-editor.as;
!	we ship an open-message and park on the reply (cancelled / profiles).
	module ScheduleEditorModule
	variable OpenMsg
	variable ScheduleResult
!	LiveProfiles is the shared scratch the remaining sheet-save handlers
!	(SaveOutsideSheet, etc) use to splice their per-sheet edits into a
!	fresh profiles array.
	variable LiveProfiles
	variable WarnMessage
	variable BoostText
	variable BoostTickI
	variable BoostTickRoom
	variable BoostTickUntil
	variable BoostTickRemaining
	variable BoostTickPrevText

!	Info sheet state.
	variable InfoSheetWebson
	variable InfoSheetOpen
	variable InfoSheetRoomIdx
	variable InfoAgeMs
	variable InfoAgeMin
	variable InfoBatteryVal
	variable InfoHumidityVal
	variable InfoRelayVal

!	System sheet state. SystemType is "Boiler" or "Heat Pump"; stored on
!	the map root so the controller can fan it out to fuel-aware logic.
	variable SystemSheetWebson
	variable EditingSystemName
	variable EditingSystemType
	variable SystemType

!	Demand-relay state. RequestRelay holds the current map.request value;
!	the in-flight editing value lives in the device-editor module while
!	its sheet is open. Save (in the module) returns the new value and a
!	`requestRelayChanged: yes|no` flag, and OpenDeviceEditor ships a
!	`Request Relay` uirequest only when the flag is yes.
	variable RequestRelay

!	Outside sheet state. The outside thermometer lives in the legacy "room
!	with empty relays" slot of every profile; sensor name and frost-trigger
!	(ptemp) are fanned out to all profiles on save. FrostActive is derived
!	per refresh from the controller's `frostActive` flag if present, else
!	computed locally (outside temp ≤ trigger and no rooms calling).
	variable OutsideSheetWebson
	variable OutsideSensor
	variable FrostTrigger
	variable EditingOutsideSensor
	variable EditingFrostTrigger
	variable FrostActive
	variable OutsideTempTenths
	variable FrostTriggerTenths
	variable NegativeFlag
	variable OutsideRoomLegacyIdx
	variable OutsideRoomFound
	variable LiveProfileForOutside
	variable LiveRoomsForOutside
	variable LiveRoomForOutside
	variable OutsideProfileLoopI

!	Device editor reply-state. The editor itself lives in device-editor.as;
!	we ship an open-message and park on the reply (cancelled / profiles /
!	requestRelay / requestRelayChanged).
	module DeviceEditorModule
	variable DeviceResult
!	OutsideSheet profile-count scratch (the var name is historic — was
!	shared with the now-extracted device editor; it's used only by
!	SaveOutsideSheet's fan-out loop).
	variable DeviceProfileCount
!! @hash 260d467c
!!!
!! Synchronous bootstrap. Runs from attach-AppRoot down to the final `stop`, building the top bar and registering the MQTT connection. Subsequent control flow is handler-driven (on resume, on click, on mqtt message, on mqtt connect).
!!
!! Sequence: attach the #app container, apply the time-of-day background gradient, render the outer three-zone layout (layout.json) and the top bar (top-bar.json). Wire the heartbeat dot, the tab-resume hook, and the hamburger button (initially bound to a credentials-reset action — re-bound to the full menu sheet later by BuildHomeScreen).
!!
!! Credentials are fetched in priority order: local credentials.json (deploy-provided, used on IXHUB/offline test installs) → server credentials.php (the shared production endpoint) → no credentials. The MAC is read from localStorage; missing broker OR missing MAC triggers demo mode, which renders demo-map.json and opens the About sheet so first-time visitors see what RBR does without any backend.
!!
!! Otherwise MQTT connects to broker:port with username/password and the per-session MyID topic. `on mqtt connect` jumps to Connected; `on mqtt message` dumps every payload through OnMapReceived. The final `stop` parks the script while the runtime drives the rest of execution through registered handlers.
!!
!! Credentials labels (TryServerCredentials / ApplyCredentials / NoCredentialsFile) are intermediate branch targets within the credentials-loading flow, not independent entry points.

	attach AppRoot to `app` or begin
		alert `Missing #app container in index.html`
		stop
	end

!	Map-to-rooms translation runs as a sub-module so the bulk of the legacy→new-UI
!	translation (~490 lines) lives in its own file. Loaded once here; called by
!	OnMapReceived on every map push via `send Map to MapToRoomsModule and assign reply to MapResult`.
!	The JS dialect's `run` takes a variable holding source code (not a filename),
!	so we fetch via `rest get` first.
	rest get ModuleSrc from `resources/as/map-to-rooms.as?v=` cat now
		or go to LoadFailed
	run ModuleSrc as MapToRoomsModule

	set style `min-height` of AppRoot to `100vh`
	gosub to ApplyBackground

!	Outer three-zone layout.
	rest get LayoutWebson from `resources/webson/layout.json?v=` cat now
		or go to LoadFailed
	render LayoutWebson in AppRoot

!	TopBar.
	attach TopBarHolder to `layout-topbar`
	rest get TopBarWebson from `resources/webson/top-bar.json?v=` cat now
		or go to LoadFailed
	render TopBarWebson in TopBarHolder

	attach SystemId to `top-bar-system-id`
	set the content of SystemId to `…`

	attach HeartbeatBtn to `top-bar-heartbeat`
	attach HeartbeatDot to `top-bar-heartbeat-dot`
	on click HeartbeatBtn gosub to RequestMap

!	Tab resume — when the OS un-throttles a backgrounded tab, the MQTT
!	WebSocket may have been silently torn down by the OS or network.
!	The MQTT client doesn't always notice, so a `send` succeeds into a
!	dead socket and no reply ever comes back. If the last message we
!	received is older than 5 minutes, force a full page reload to rebuild
!	MQTT from scratch. For shorter resumes (briefly switched apps), just
!	trigger an immediate refresh.
	on resume
	begin
		log `Tab resumed`
!		Don't try to RequestMap before MQTT has connected and the first
!		map cycle has run — the topic objects and Prompt aren't reliably
!		set yet, and the next normal poll will catch up on its own.
		if not FirstMapDone return
		if LastReceivedAt is not empty
		begin
			put now into ResumeAge
			take LastReceivedAt from ResumeAge
			if ResumeAge is greater than 300000
			begin
				log `Stale data on resume (` cat ResumeAge cat ` ms); reloading`
				location the location
				return
			end
		end
		gosub to RequestMap
	end

!	Panic-button for stranded credentials. The hamburger button is the only
!	always-visible UI element, so wire it now (synchronously, before MQTT)
!	to a credentials-reset action. BuildHomeScreen re-binds it later for
!	the full menu sheet, so this handler only fires when BuildHomeScreen
!	never ran (i.e. MQTT hasn't connected and no map has arrived).
	attach MenuButton to `top-bar-menu-btn`
	on click MenuButton gosub to ResetCredentialsAndReload

!	Day-of-week and month-name lookup tables for the SummaryCard date.
!	`the day` is JS getDay (0=Sun); `the month` is getMonth (0=Jan).
	put `[]` into DayNames
	set element 0 of DayNames to `Sun`
	set element 1 of DayNames to `Mon`
	set element 2 of DayNames to `Tue`
	set element 3 of DayNames to `Wed`
	set element 4 of DayNames to `Thu`
	set element 5 of DayNames to `Fri`
	set element 6 of DayNames to `Sat`

	put `[]` into MonthNames
	set element 0 of MonthNames to `Jan`
	set element 1 of MonthNames to `Feb`
	set element 2 of MonthNames to `Mar`
	set element 3 of MonthNames to `Apr`
	set element 4 of MonthNames to `May`
	set element 5 of MonthNames to `Jun`
	set element 6 of MonthNames to `Jul`
	set element 7 of MonthNames to `Aug`
	set element 8 of MonthNames to `Sep`
	set element 9 of MonthNames to `Oct`
	set element 10 of MonthNames to `Nov`
	set element 11 of MonthNames to `Dec`

!	MQTT credentials. The broker / port / username / password are shared
!	across all customers and served by credentials.php (which reads from
!	`../<HTTP_HOST>.txt` — see credentials.example.json for the schema).
!	The per-system MAC is the only thing the user has to enter, and we
!	cache it in localStorage so the prompt fires only on first run.
!
!	A site-local credentials.json (deploy-provided) takes priority over
!	the shared endpoint — useful for offline / on-IXHUB testing where
!	credentials.php isn't reachable.
	no cache
	rest get Credentials from `credentials.json`
		or go to TryServerCredentials
	if Credentials is not empty go to ApplyCredentials
TryServerCredentials:
!	credentials.php lives at the site root, one level above new-ui/.
	rest get Credentials from `../credentials.php`
		or go to NoCredentialsFile
ApplyCredentials:
	if Credentials is not empty
	begin
		put property `broker` of Credentials into Broker
		put property `port` of Credentials into Port
		put property `username` of Credentials into Username
		put property `password` of Credentials into Password
		if Broker is `localhost`
		begin
			if the hostname is not `localhost` put the hostname into Broker
		end
	end
NoCredentialsFile:
!	MAC is per-system and never lives on the server. Read it from
!	localStorage so the user only has to enter it once.
	get MAC from storage as `dev-mac`
	if MAC is `null` put empty into MAC
	if MAC is `undefined` put empty into MAC

!	No usable credentials → demo / marketing mode. We need a broker (either
!	from credentials.json / credentials.php) and a MAC (from localStorage).
!	Either missing → render the home from a baked demo map and open the
!	About sheet so first-time visitors see what RBR does. Skip MQTT.
	clear DemoMode
	if Broker is empty set DemoMode
	if MAC is empty set DemoMode
	if DemoMode
	begin
		rest get ReceivedMessage from `demo-map.json?v=` cat now
			or go to LoadFailed
		gosub to OnMapReceived
		gosub to OpenAboutSheet
		stop
	end

	if Port is empty put 443 into Port
	put `RBR-` cat random 999999 into MyID

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
		subscribe MyTopic

	on mqtt connect
	begin
		log `MQTT Connected`
		go to Connected
	end

	on mqtt message
	begin
		put the mqtt message into ReceivedMessage
		gosub to OnMapReceived
	end
	stop
!! @hash 35bfa8e5
!!!
!! First-render path: fired by `on mqtt connect`. Sets the Prompt to `first` so the controller sends a full map (rather than the empty-payload heartbeat used for refreshes), then forks a watchdog and parks.
!!
!! The watchdog handles a common mobile failure mode where the WebSocket opens but the MQTT subscription is silently dropped before the controller's reply lands — without it the UI hangs forever showing the loading state. Capped at 3 attempts via localStorage so a genuinely unreachable controller doesn't become an infinite reload loop.
Connected:
	put `first` into Prompt
	clear FirstMapDone
	gosub to RequestMap
	fork to FirstMapWatchdog
	stop
!! @hash 188df672
!!!
!! Forked watchdog. Sleeps 30 seconds; if the first map still hasn't arrived, the MQTT subscription is almost certainly dead — force a full reload to rebuild the connection. Capped at 3 attempts via localStorage so an unreachable controller is reported with an alert rather than an infinite reload loop.
FirstMapWatchdog:
	wait 30 seconds
	if FirstMapDone return
	log `First map didn't arrive in 30s`
	get FirstMapAttempts from storage as `first-map-attempts`
	if FirstMapAttempts is `null` put 0 into FirstMapAttempts
	if FirstMapAttempts is `undefined` put 0 into FirstMapAttempts
	if FirstMapAttempts is empty put 0 into FirstMapAttempts
	increment FirstMapAttempts
	put FirstMapAttempts into storage as `first-map-attempts`
	if FirstMapAttempts is greater than 2
	begin
		alert `Cannot reach controller. Please check your network and reload.`
		return
	end
	log `Reloading (first-map attempt ` cat FirstMapAttempts cat `)`
	location the location
	return
!! @hash 4fe2712f
!!!
!! Send a single map request to the controller. Used both for the initial `first` push and the recurring `refresh` heartbeat — the action string is whatever Prompt happens to hold.
!!
!! Default the Prompt to `refresh` if it's empty so a spurious early call (e.g. on resume firing during a window where the page backgrounded mid-load) can't trigger the runtime's "missing action field" check on the controller side. Send failure is logged but otherwise silent — the next poll cycle retries, and persistent failures eventually trip the staleness watchdog.
RequestMap:
	if Prompt is empty put `refresh` into Prompt
	log `Requesting map: ` cat Prompt
	if not DemoMode
	begin
		send to ServerTopic
			sender MyTopic
			action Prompt
			giving SendOK
		if not SendOK log `MQTT poll send failed; will retry next cycle`
	end
	return
!! @hash db7f9c56
!!!
!! Briefly tint the topbar heartbeat dot to confirm a fresh reply arrived.
!!
!! Pulsing on RECEIVE rather than send means a dead-but-not-yet-detected WebSocket (common after a phone wake-up) shows up as the dot going quiet — an honest signal — instead of false-positive pulses from a send that "succeeded" into a closed socket. Called from OnMapReceived for every reply (full map or empty heartbeat ping), since either proves the round-trip is alive.
PulseHeartbeat:
	set style `background-color` of HeartbeatDot to `var(--color-accent)`
	wait 50 ticks
	set style `background-color` of HeartbeatDot to `rgba(0,0,0,0.18)`
	return
!! @hash 2ad91a5c
!!!
!! Fired by `on mqtt message`. Routes incoming controller payloads into the right render path: BuildHomeScreen for the first one, RefreshHomeScreen thereafter.
!!
!! The controller replies to every refresh — with the full map when state has changed, otherwise with an empty payload that's purely a round-trip ping. We update LastReceivedAt and pulse the heartbeat for *any* reply (the connection is healthy) but only do render work when there's actual map data.
!!
!! Validates BEFORE clobbering Map: a ping or malformed payload that overwrites Map.profiles would silently corrupt every Save handler (they read Map.profiles to build their `uirequests`). On invalid input we discard and preserve the previous Map.
!!
!! After the first successful build, fork to MapPollTask to keep the UI in sync. Skipped in demo mode (no controller to poll).
OnMapReceived:
	put now into LastReceivedAt
	gosub to PulseHeartbeat
	if ReceivedMessage is empty
	begin
		increment HeartbeatCount
		return
	end
!	Validate BEFORE clobbering Map. A ping or malformed payload that
!	overwrites Map.profiles silently corrupts every Save handler (they
!	read Map.profiles to build their uirequests). Either form (empty
!	payload, or payload-without-profiles) is the controller's heartbeat
!	reply — count it and drop, so we get one summary line per real map
!	rather than one log line per poll.
	if property `profiles` of ReceivedMessage is empty
	begin
		increment HeartbeatCount
		put empty into ReceivedMessage
		return
	end
	if HeartbeatCount is greater than 0
	begin
		log `OnMapReceived: ` cat HeartbeatCount cat ` heartbeats since last map`
		put 0 into HeartbeatCount
	end
!	Diagnostic: dump the full payload so it can be pasted into JSON Lint
!	to verify structure if anything downstream complains. Comment out
!	once the bug is hunted down — these payloads are large.
	log `OnMapReceived: applying new map`
!	log ReceivedMessage
	put ReceivedMessage into Map
	put empty into ReceivedMessage
!	Ship the legacy map to the translation module and unpack the reply into our globals.
	send Map to MapToRoomsModule and assign reply to MapResult
	put property `rooms` of MapResult into RoomsList
	put property `roomCount` of MapResult into RoomCount
	put property `outsideTemp` of MapResult into OutsideTemp
	put property `outsideSensor` of MapResult into OutsideSensor
	put property `frostTrigger` of MapResult into FrostTrigger
	clear OutsideRoomFound
	if property `outsideRoomFound` of MapResult is `yes` set OutsideRoomFound
	put property `outsideRoomLegacyIdx` of MapResult into OutsideRoomLegacyIdx
	put property `profiles` of MapResult into Profiles
	put property `currentProfile` of MapResult into CurrentProfile
	put property `activeProfile` of MapResult into ActiveProfile
	put property `activeProfileName` of MapResult into ActiveProfileName
	put property `systemName` of MapResult into SystemName
	put property `systemType` of MapResult into SystemType
	put property `requestRelay` of MapResult into RequestRelay
	clear CalendarOn
	if property `calendarOn` of MapResult is `on` set CalendarOn
	if not FirstMapDone
	begin
		set FirstMapDone
		put 0 into storage as `first-map-attempts`
		gosub to BuildHomeScreen
		put `refresh` into Prompt
		if not DemoMode fork to MapPollTask
	end
	else
	begin
		gosub to RefreshHomeScreen
	end
	return
!! @hash 2dd4d4b4
!!!
!! 10-second poll loop forked once OnMapReceived has built the home screen. Each cycle: wait 10 seconds, request a fresh map, then check how long it's been since the last reply.
!!
!! If we go more than 60 seconds (six missed cycles) with the tab visible, the MQTT WebSocket is almost certainly dead — common on mobile when the OS / carrier NAT closes idle sockets without the client noticing. Force a reload to rebuild MQTT from scratch.
MapPollTask:
	while true
	begin
		wait 10 seconds
		gosub to RequestMap
		if LastReceivedAt is not empty
		begin
			put now into ResumeAge
			take LastReceivedAt from ResumeAge
			if ResumeAge is greater than 60000
			begin
				log `No MQTT replies for ` cat ResumeAge cat ` ms; reloading`
				location the location
				return
			end
		end
	end
!! @hash beb328fa
!!!
!! One-shot home-screen builder. Runs on the first non-empty map, never again — subsequent updates go through RefreshHomeScreen.
!!
!! Two render passes plus sheet chrome. Pass 1: SummaryCard into MainHolder (rendered first so it sits visually on top of the room list). Pass 2: each RoomRow into MainHolder via the room-row.json template, with `/I/` substituted for the room index — every row's element IDs include this index so each handler can recover its row via `the index of X`.
!!
!! Sheet chrome (sheet.json) is rendered once into AppRoot; each subsequent sheet (Menu, Profile, Schedule, Device, System, Outside, Info, About) is rendered into SheetContent and starts at display:none. HideAllSheets is the single chokepoint that prevents one sheet bleeding through another.
!!
!! Every indexed per-row variable (RestRow, InfoBtn, ExpansionEl, ModeTimedBtn, etc.) MUST be pre-sized with `set the elements of X to RoomCount` before any `index X to N` for N > 0 — the array has to be allocated first, otherwise the index call raises "out of range".
!!
!! Forks BackgroundTick and BoostTick at the end so the gradient and per-room boost countdowns keep ticking independently of map pushes.
BuildHomeScreen:
!	First-pass summary stats from the freshly-built RoomsList.
	gosub to ComputeSummaryStats

!	Render SummaryCard into the main column (before the rooms so it sits on top).
	attach MainHolder to `layout-main`
	rest get SummaryWebson from `resources/webson/summary-card.json?v=` cat now
		or go to LoadFailed
	render SummaryWebson in MainHolder

	attach SummaryTitle to `summary-title`
	attach SummarySubtitle to `summary-subtitle`
	attach SummaryAvg to `summary-avg`
	attach SummaryOutside to `summary-outside`
	attach SummaryOutsideFrost to `summary-outside-frost`
	attach SummaryToday to `summary-today`
	attach SummaryProfileName to `summary-profile-name`
	attach SummaryChip to `summary-chip`
	attach SummaryChipIcon to `summary-chip-icon`
	attach SummaryDot to `summary-chip-dot`

	gosub to PaintSummary

!	Profile pill click — open ProfileSheet (wired below, after sheet chrome
!	is built; the attach here just binds the element so styling/listeners
!	hook into the right DOM node).
	attach ProfilePill to `summary-profile-pill`

!	Second pass — render each RoomRow.
	rest get RoomRowText from `resources/webson/room-row.json?v=` cat now
		or go to LoadFailed

	put -1 into ExpandedIndex

	put -1 into BoostPanelOpenIndex
!	Pre-size every indexed per-row variable. Without this, `index X to N`
!	for N > 0 raises "out of range" — the array has to be allocated first.
	set the elements of RestRow to RoomCount
	set the elements of InfoBtn to RoomCount
	set the elements of ExpansionEl to RoomCount
	set the elements of TargetBlockEl to RoomCount
	set the elements of TargetValueEl to RoomCount
	set the elements of BoostBlockEl to RoomCount
	set the elements of ModeTimedBtn to RoomCount
	set the elements of ModeBoostBtn to RoomCount
	set the elements of ModeOnBtn to RoomCount
	set the elements of ModeOffBtn to RoomCount
	set the elements of TargetMinusBtn to RoomCount
	set the elements of TargetPlusBtn to RoomCount
	set the elements of Boost30Btn to RoomCount
	set the elements of Boost1hBtn to RoomCount
	set the elements of Boost2hBtn to RoomCount
	set the elements of BoostOffBtn to RoomCount
	set the elements of AdvanceBlockEl to RoomCount
	set the elements of AdvanceBtn to RoomCount
	set the elements of EditScheduleBtn to RoomCount

	put 0 into RoomIndex
	while RoomIndex is less than RoomCount
	begin
		put RoomRowText into RowText
		put `` cat RoomIndex into IndexStr
		replace `/I/` with IndexStr in RowText
		render RowText in MainHolder

		put element RoomIndex of RoomsList into Room
		gosub to RenderRoom

!		Sensor rows have no chevron, no expansion, no interactions.
		put property `sensor` of Room into Sensor
		if Sensor is `no` gosub to WireRoomInteractions

		increment RoomIndex
	end

!	Sheet chrome — once, into AppRoot. Container is position:fixed so parent
!	doesn't matter visually, but keeping it under AppRoot keeps the DOM tidy.
	rest get SheetWebson from `resources/webson/sheet.json?v=` cat now
		or go to LoadFailed
	render SheetWebson in AppRoot

	attach SheetContent to `sheet-content`
	rest get MenuWebson from `resources/webson/menu-sheet.json?v=` cat now
		or go to LoadFailed
	render MenuWebson in SheetContent

	attach MenuSheetEl to `menu-sheet`
!	ProfileSheet lives in its own module (profile-sheet.as). It renders its
!	sheet into the same sheet-content container, attaches its own DOM, and
!	wires its own click handlers. Loaded below; the local ProfileSheetEl
!	handle exists only so HideAllSheets can hide it when another sheet opens.

	attach SheetRoot to `sheet-root`
	attach SheetScrim to `sheet-scrim`
	attach SheetContainer to `sheet-container`
	attach SheetCloseBtn to `sheet-close-btn`
	attach SheetTitleEl to `sheet-title`

	on click SheetCloseBtn gosub to CloseSheet
	on click SheetScrim gosub to CloseSheet

!	Menu row click handlers. System / Devices / Outside open their own
!	sheets; Help is wired but inactive (no target sheet yet — placeholder
!	for a future help/about flow).
	attach MenuRowSystem to `menu-row-system`
	on click MenuRowSystem gosub to OpenSystemSheet
	attach MenuRowDevices to `menu-row-devices`
	on click MenuRowDevices gosub to OpenDeviceEditor
	attach MenuRowOutside to `menu-row-outside`
	on click MenuRowOutside gosub to OpenOutsideSheet
	attach MenuRowHelp to `menu-row-help`
	on click MenuRowHelp
	begin
		log `Menu: Help & support (stub)`
	end

!	Hook up the top-bar menu button now that the sheet is ready.
	attach MenuButton to `top-bar-menu-btn`
	on click MenuButton
	begin
		gosub to HideAllSheets
		set style `display` of MenuSheetEl to `block`
		set the content of SheetTitleEl to `Menu`
		gosub to OpenSheet
	end

!	Profile pill opens the combined ProfileSheet. Snapshot of state is taken
!	at open time; all changes batch through Save / discard via Cancel.
	on click ProfilePill gosub to OpenProfileSheet

!	Profile sheet module — owns the sheet DOM (profile list, calendar header,
!	day grid, per-day pickers) and its editing flow. Loaded after sheet-content
!	exists; parks on `on message` until the user taps the profile pill.
	rest get ModuleSrc from `resources/as/profile-sheet.as?v=` cat now
		or go to LoadFailed
	run ModuleSrc as ProfileSheetModule
!	Local handle to the sheet element the module rendered, so HideAllSheets
!	can hide it when another sheet opens.
	attach ProfileSheetEl to `profile-sheet`

!	Schedule editor lives in its own module (schedule-editor.as). The module
!	renders its sheet into the same sheet-content container, attaches its own
!	DOM, and wires its own click handlers. Loaded here (after sheet-content
!	exists) and parks on `on message` until the user clicks Edit Schedule
!	for a room — OpenScheduleEditor below ships the open-payload and blocks
!	on the reply.
	rest get ModuleSrc from `resources/as/schedule-editor.as?v=` cat now
		or go to LoadFailed
	run ModuleSrc as ScheduleEditorModule
!	Local handle to the sheet element the module rendered, so HideAllSheets
!	can hide it when another sheet opens.
	attach ScheduleSheetEl to `schedule-editor-sheet`

!	Device editor lives in its own module (device-editor.as). Loaded here
!	(after sheet-content exists) and parks on `on message` until the user
!	clicks the menu's "Devices" row — OpenDeviceEditor below ships the
!	open-payload and blocks on the reply.
	rest get ModuleSrc from `resources/as/device-editor.as?v=` cat now
		or go to LoadFailed
	run ModuleSrc as DeviceEditorModule
!	Local handle to the sheet element the module rendered, so HideAllSheets
!	can hide it when another sheet opens.
	attach DeviceEditorSheetEl to `device-editor-sheet`

!	System type & name sheet — opened from the menu's "System type & name"
!	row. Edits the map's name + systemType fields.
	rest get SystemSheetWebson from `resources/webson/system-sheet.json?v=` cat now
		or go to LoadFailed
	render SystemSheetWebson in SheetContent
	attach SystemSheetEl to `system-sheet`
	set style `display` of SystemSheetEl to `none`
	attach SystemSheetName to `system-sheet-name`
	attach SystemSheetTypeBoiler to `system-sheet-type-boiler`
	attach SystemSheetTypeHeatPump to `system-sheet-type-heatpump`
	attach SystemSheetSaveBtn to `system-sheet-save-btn`
	attach SystemSheetCancelBtn to `system-sheet-cancel-btn`

	on click SystemSheetTypeBoiler
	begin
		put `Boiler` into EditingSystemType
		gosub to PaintSystemSheetType
	end
	on click SystemSheetTypeHeatPump
	begin
		put `Heat Pump` into EditingSystemType
		gosub to PaintSystemSheetType
	end
	on click SystemSheetSaveBtn gosub to SaveSystemSheet
	on click SystemSheetCancelBtn gosub to CloseSheet

!	Outside thermometer + frost protection sheet — opened from the menu's
!	"Outside thermometer" row. Edits the sensor and ptemp on the legacy
!	"room with empty relays" slot of every profile.
	rest get OutsideSheetWebson from `resources/webson/outside-sheet.json?v=` cat now
		or go to LoadFailed
	render OutsideSheetWebson in SheetContent
	attach OutsideSheetEl to `outside-sheet`
	set style `display` of OutsideSheetEl to `none`
	attach OutsideSheetSensor to `outside-sheet-sensor`
	attach OutsideSheetFrost to `outside-sheet-frost`
	attach OutsideSheetSaveBtn to `outside-sheet-save-btn`
	attach OutsideSheetCancelBtn to `outside-sheet-cancel-btn`
	on click OutsideSheetSaveBtn gosub to SaveOutsideSheet
	on click OutsideSheetCancelBtn gosub to CloseSheet

!	Info sheet — opened from each room row's info button.
	rest get InfoSheetWebson from `resources/webson/info-sheet.json?v=` cat now
		or go to LoadFailed
	render InfoSheetWebson in SheetContent
	attach InfoSheetEl to `info-sheet`
	set style `display` of InfoSheetEl to `none`
	attach InfoRelayValue to `info-relay`
	attach InfoTempValue to `info-temp`
	attach InfoHumidityValue to `info-humidity`
	attach InfoBatteryValue to `info-battery`
	attach InfoAgeValue to `info-age`

!	About sheet — sibling sheet inside sheet-content. Auto-opens on first
!	visit when there are no credentials; tap the house mark in the topbar
!	to re-open at any time.
	rest get AboutSheetWebson from `resources/webson/about-sheet.json?v=` cat now
		or go to LoadFailed
	render AboutSheetWebson in SheetContent
	attach AboutSheetEl to `about-sheet`
	set style `display` of AboutSheetEl to `none`
	attach AboutTabAbout to `about-tab-about`
	attach AboutTabManual to `about-tab-manual`
	attach AboutBodyAbout to `about-body-about`
	attach AboutBodyManual to `about-body-manual`
	attach AboutCtaSetup to `about-cta-setup`

	on click AboutTabAbout gosub to ShowAboutTabAbout
	on click AboutTabManual gosub to ShowAboutTabManual
	on click AboutCtaSetup gosub to SetupMySystem

	attach HouseMark to `top-bar-mark`
	on click HouseMark gosub to OpenAboutSheet

!	All sibling sheets are now attached — flag the world ready so
!	HideAllSheets stops being a no-op when called from click handlers.
	set SheetsReady

!	Background tick — re-pick the gradient at hour boundaries. Forked once
!	on first build; subsequent refreshes don't re-fork.
	fork to BackgroundTick

!	Boost-countdown tick — re-derive "N mins left" locally between map
!	pushes so a quiet room's countdown doesn't appear frozen.
	fork to BoostTick

	return
!! @hash 116cebd7
!!!
!! Refresh path on every subsequent map push. Re-renders every room in place via RenderRoom and recomputes the summary.
!!
!! Assumes RoomCount is unchanged from the initial build — adding or removing rooms takes a Save through the Devices sheet plus a fresh map, and the controller-side handler currently sends a full new map (which OnMapReceived treats as a refresh, not a first-build). If RoomCount changes silently the indexed per-row variables will be the wrong size.
!!
!! If a room's expansion panel is open, repaint its inner controls so a controller-side change (e.g. the legacy UI changed mode for that room) propagates immediately rather than waiting for the user to close-and-reopen the expansion. Same logic for an open Info sheet.
RefreshHomeScreen:
	put 0 into RoomIndex
	while RoomIndex is less than RoomCount
	begin
		put element RoomIndex of RoomsList into Room
		put `` cat RoomIndex into IndexStr
		gosub to RenderRoom
		increment RoomIndex
	end
	gosub to ComputeSummaryStats
	gosub to PaintSummary
	if ExpandedIndex is not -1
	begin
		put ExpandedIndex into ClickIndex
		gosub to PaintExpansion
	end
	if InfoSheetOpen
	begin
		put element InfoSheetRoomIdx of RoomsList into Room
		gosub to PaintInfoSheet
	end
	return
!! @hash d559715a
!!!
!! Parse TempStr ("HH:MM" or "H:MM") into minutes-since-midnight; output via TempTenths (the variable name is historic — it carries minutes here, not tenths). Empty / malformed input yields 0.
ParseTimeMinutes:
	put 0 into TempTenths
	if TempStr is empty return
	put the index of `:` in TempStr into DotIdx
	if DotIdx is less than 0 return
	put the value of left DotIdx of TempStr into TempTenths
	multiply TempTenths by 60
	increment DotIdx
	put the value of from DotIdx of TempStr into DecPart
	add DecPart to TempTenths
	return
!! @hash 3a38eab5
!!!
!! Pick the time-of-day gradient stops by hour bucket and apply both a linear gradient and a soft white radial glow to AppRoot in one stacked background.
!!
!! Six hour buckets: 0–6 (night/early-morning), 6–10 (dawn), 10–15 (midday), 15–19 (afternoon), 19–22 (sunset), 22+ (night). Cards and sheets sit in front via normal CSS stacking.
!!
!! `background-attachment: fixed` keeps the gradient anchored to the viewport when the room list scrolls, which costs nothing on modern mobile.
ApplyBackground:
	put the hour into Hour
	put `#FDF6EC` into GTop
	put `#FBEEDD` into GMid
	put `#F5E2C9` into GBot
	if Hour is less than 6
	begin
		put `#1E2238` into GTop
		put `#2D2A3E` into GMid
		put `#433048` into GBot
	end
	else if Hour is less than 10
	begin
		put `#FFE8D4` into GTop
		put `#FFD3B0` into GMid
		put `#F5B994` into GBot
	end
	else if Hour is less than 15
	begin
		put `#FDF6EC` into GTop
		put `#FBEEDD` into GMid
		put `#F5E2C9` into GBot
	end
	else if Hour is less than 19
	begin
		put `#FFE1C2` into GTop
		put `#F7B88A` into GMid
		put `#E88A5B` into GBot
	end
	else if Hour is less than 22
	begin
		put `#F0A877` into GTop
		put `#B66B56` into GMid
		put `#5A3A52` into GBot
	end
	else
	begin
		put `#1E2238` into GTop
		put `#2D2A3E` into GMid
		put `#433048` into GBot
	end
	put `radial-gradient(ellipse at 50% -20%, rgba(255,255,255,0.5) 0%, transparent 70%)` into Glow
	put Glow cat `, linear-gradient(180deg, ` cat GTop cat ` 0%, ` cat GMid cat ` 45%, ` cat GBot cat ` 100%)` into BgValue
	set style `background` of AppRoot to BgValue
	set style `background-attachment` of AppRoot to `fixed`
	return
!! @hash da4604ae
!!!
!! Forked once on first build. Polls `the hour` once a minute and re-applies ApplyBackground if the hour bucket changed. A minute is fine — bucket boundaries don't need sub-minute precision and a one-minute lag at the transition is invisible to the user.
BackgroundTick:
	put the hour into LastHour
	while true
	begin
		wait 60 seconds
		put the hour into Hour
		if Hour is not LastHour
		begin
			put Hour into LastHour
			gosub to ApplyBackground
		end
	end
!! @hash 5369729b
!!!
!! Forked once on first build. Re-derives the "N mins left" text on every boosted room every 30 seconds.
!!
!! The controller only pushes a fresh map when state changes (temperature / period / relay), so on a quiet room mid-boost the displayed countdown text would otherwise stay frozen between pushes. This tick is purely cosmetic — the controller still owns the actual expiry timestamp, and the countdown is recomputed from `boostUntilMs` (the absolute end time the controller set when the boost was applied).
!!
!! When the text changes we re-render the room row in place so the chip / subline update immediately, without waiting for the next refresh.
BoostTick:
	while true
	begin
		wait 30 seconds
		if RoomCount is greater than 0
		begin
			put 0 into BoostTickI
			while BoostTickI is less than RoomCount
			begin
				put element BoostTickI of RoomsList into BoostTickRoom
				if property `mode` of BoostTickRoom is `Boost`
				begin
					put property `boostUntilMs` of BoostTickRoom into BoostTickUntil
					if BoostTickUntil is not empty
					begin
						put BoostTickUntil into BoostTickRemaining
						take the timestamp from BoostTickRemaining
						if BoostTickRemaining is greater than 0
						begin
							divide BoostTickRemaining by 60000
							add 1 to BoostTickRemaining
							if BoostTickRemaining is 1 put `1 min` into BoostText
							else put BoostTickRemaining cat ` mins` into BoostText
							put property `boost` of BoostTickRoom into BoostTickPrevText
							if BoostTickPrevText is not BoostText
							begin
								set property `boost` of BoostTickRoom to BoostText
								set property `boostRemaining` of BoostTickRoom to BoostTickRemaining
								set element BoostTickI of RoomsList to BoostTickRoom
								put BoostTickRoom into Room
								put BoostTickI into RoomIndex
								put `` cat RoomIndex into IndexStr
								gosub to RenderRoom
							end
						end
					end
				end
				increment BoostTickI
			end
		end
	end
!! @hash 15347efe
!!!
!! Open / close the bottom sheet. CSS transitions handle the motion; the code just flips opacity, transform, and the root's pointer-events. CloseSheet is the mirror image.
OpenSheet:
	set style `pointer-events` of SheetRoot to `auto`
	set style `opacity` of SheetScrim to `1`
	set style `transform` of SheetContainer to `translateY(0)`
	return

CloseSheet:
	set style `opacity` of SheetScrim to `0`
	set style `transform` of SheetContainer to `translateY(100%)`
	set style `pointer-events` of SheetRoot to `none`
	return
!! @hash 5de73def
!!!
!! Hide every sibling sheet under sheet-content. Each Open<X> routine must call this before flipping a single sheet's display:block — the single chokepoint that prevents one sheet bleeding through another.
!!
!! The SheetsReady gate prevents a tap during BuildHomeScreen — when the menu button has been wired but later sheets aren't attached yet — from runtime-erroring on an unattached element.
HideAllSheets:
	if not SheetsReady return
	set style `display` of MenuSheetEl to `none`
	set style `display` of ProfileSheetEl to `none`
	set style `display` of ScheduleSheetEl to `none`
	set style `display` of DeviceEditorSheetEl to `none`
	set style `display` of SystemSheetEl to `none`
	set style `display` of OutsideSheetEl to `none`
	set style `display` of InfoSheetEl to `none`
	set style `display` of AboutSheetEl to `none`
	return
!! @hash 56513531
!!!
!! Wire every interactive element of a single room row. Called once per non-sensor row from the BuildHomeScreen render loop, with RoomIndex pre-set to the row being wired.
!!
!! Indexes each per-row element (RestRow, InfoBtn, ExpansionEl, the four mode buttons, target +/- , the four boost buttons, advance, edit-schedule) to its row, attaches each to the DOM id pattern `room-<i>-<element>`, and registers a click handler. Click handlers recover their firing row via `the index of X` and dispatch to the appropriate routine after capturing ClickIndex.
!!
!! Sensor (outdoor) rows skip this entirely — they have no chevron, no expansion, no interactions.
WireRoomInteractions:
	index RestRow to RoomIndex
	attach RestRow to `room-` cat RoomIndex cat `-rest`
	on click RestRow
	begin
		put the index of RestRow into ClickIndex
		gosub to ToggleExpansion
	end

	index InfoBtn to RoomIndex
	attach InfoBtn to `room-` cat RoomIndex cat `-info-btn`
	on click InfoBtn
	begin
		put the index of InfoBtn into ClickIndex
		gosub to OpenInfoSheet
	end
	index ExpansionEl to RoomIndex
	attach ExpansionEl to `room-` cat RoomIndex cat `-expansion`
	index TargetBlockEl to RoomIndex
	attach TargetBlockEl to `room-` cat RoomIndex cat `-target-block`
	index BoostBlockEl to RoomIndex
	attach BoostBlockEl to `room-` cat RoomIndex cat `-boost-block`
	index TargetValueEl to RoomIndex
	attach TargetValueEl to `room-` cat RoomIndex cat `-target-value`

	index ModeTimedBtn to RoomIndex
	attach ModeTimedBtn to `room-` cat RoomIndex cat `-mode-timed`
	on click ModeTimedBtn
	begin
		put the index of ModeTimedBtn into ClickIndex
		put `Timed` into NewMode
		gosub to ChangeMode
	end
	index ModeBoostBtn to RoomIndex
	attach ModeBoostBtn to `room-` cat RoomIndex cat `-mode-boost`
	on click ModeBoostBtn
	begin
		put the index of ModeBoostBtn into ClickIndex
		gosub to OpenBoostPanel
	end
	index ModeOnBtn to RoomIndex
	attach ModeOnBtn to `room-` cat RoomIndex cat `-mode-on`
	on click ModeOnBtn
	begin
		put the index of ModeOnBtn into ClickIndex
		put `On` into NewMode
		gosub to ChangeMode
	end
	index ModeOffBtn to RoomIndex
	attach ModeOffBtn to `room-` cat RoomIndex cat `-mode-off`
	on click ModeOffBtn
	begin
		put the index of ModeOffBtn into ClickIndex
		put `Off` into NewMode
		gosub to ChangeMode
	end

	index TargetMinusBtn to RoomIndex
	attach TargetMinusBtn to `room-` cat RoomIndex cat `-target-minus`
	on click TargetMinusBtn
	begin
		put the index of TargetMinusBtn into ClickIndex
		gosub to StepTargetDown
	end
	index TargetPlusBtn to RoomIndex
	attach TargetPlusBtn to `room-` cat RoomIndex cat `-target-plus`
	on click TargetPlusBtn
	begin
		put the index of TargetPlusBtn into ClickIndex
		gosub to StepTargetUp
	end

	index Boost30Btn to RoomIndex
	attach Boost30Btn to `room-` cat RoomIndex cat `-boost-30`
	on click Boost30Btn
	begin
		put the index of Boost30Btn into ClickIndex
		put `30 min` into BoostDur
		gosub to ApplyBoost
	end
	index Boost1hBtn to RoomIndex
	attach Boost1hBtn to `room-` cat RoomIndex cat `-boost-1h`
	on click Boost1hBtn
	begin
		put the index of Boost1hBtn into ClickIndex
		put `1 hr` into BoostDur
		gosub to ApplyBoost
	end
	index Boost2hBtn to RoomIndex
	attach Boost2hBtn to `room-` cat RoomIndex cat `-boost-2h`
	on click Boost2hBtn
	begin
		put the index of Boost2hBtn into ClickIndex
		put `2 hr` into BoostDur
		gosub to ApplyBoost
	end

	index BoostOffBtn to RoomIndex
	attach BoostOffBtn to `room-` cat RoomIndex cat `-boost-off`
	on click BoostOffBtn
	begin
		put the index of BoostOffBtn into ClickIndex
		gosub to BoostOffTapped
	end

	index AdvanceBlockEl to RoomIndex
	attach AdvanceBlockEl to `room-` cat RoomIndex cat `-advance-block`
	index AdvanceBtn to RoomIndex
	attach AdvanceBtn to `room-` cat RoomIndex cat `-advance-btn`
	on click AdvanceBtn
	begin
		put the index of AdvanceBtn into ClickIndex
		gosub to ToggleAdvance
	end

	index EditScheduleBtn to RoomIndex
	attach EditScheduleBtn to `room-` cat RoomIndex cat `-edit-schedule`
	on click EditScheduleBtn
	begin
		put the index of EditScheduleBtn into ClickIndex
		gosub to OpenScheduleEditor
	end
	return
!! @hash 5c4af55e
!!!
!! Toggle the expansion panel for the row at ClickIndex. Only one expansion can be open at a time; if a different row's panel is already open, close it first. Also drops any in-flight Boost-configuring panel state from the previously-open row.
ToggleExpansion:
	if ExpandedIndex is not -1
	begin
		index ExpansionEl to ExpandedIndex
		set style `display` of ExpansionEl to `none`
		if ExpandedIndex is ClickIndex
		begin
			put -1 into ExpandedIndex
			put -1 into BoostPanelOpenIndex
			return
		end
	end
!	Closing one expansion to open another — drop any in-flight Boost panel
!	from the previously-open row.
	put -1 into BoostPanelOpenIndex
	index ExpansionEl to ClickIndex
	set style `display` of ExpansionEl to `flex`
	put ClickIndex into ExpandedIndex
	gosub to PaintExpansion
	return
!! @hash e736fc0c
!!!
!! Paint the expansion controls for room ClickIndex. Three boost-related UI states drive visibility / highlight:
!!
!! `active` — Room.mode == "Boost" (controller boost in progress).
!!
!! `configuring` — BoostPanelOpenIndex == ClickIndex AND mode != "Boost" (the user has tapped the Boost mode button but hasn't yet picked a duration).
!!
!! `none` — neither.
!!
!! Layout matrix (mode × state):
!!
!! Timed / none → Timed pill lit, Advance row visible, Target and Boost rows hidden.
!!
!! Timed / configuring → Timed pill lit, Target row visible (Room.target), Advance hidden, Boost row visible with Off lit.
!!
!! On / none → On pill lit, Target row visible (Room.target), Advance and Boost rows hidden.
!!
!! On / configuring → On pill lit, Target visible (Room.target), Advance hidden, Boost row visible with Off lit.
!!
!! Off / none → Off pill lit, all rows hidden.
!!
!! Off / configuring → Off pill lit, Target visible (Room.target), Advance hidden, Boost row visible with Off lit.
!!
!! Boost / active → Boost pill lit, Target visible (Room.target), Advance hidden, Boost row visible with no duration lit (duration buttons act as "replace duration" while a boost is running; Off cancels).
!!
!! Boost and On share a single target (Room.target). The tile shows Room.target in every visible state; +/- edits are committed immediately regardless of which mode is in scope.
!!
!! The mode pill in Configuring stays on the underlying mode — Boost only becomes "selected" once the user commits a duration via ApplyBoost.
PaintExpansion:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	put property `target` of Room into Ttarget

	put `none` into BoostState
	if Tmode is `Boost` put `active` into BoostState
	else if BoostPanelOpenIndex is ClickIndex put `configuring` into BoostState

!	Mode pill highlight.
	index ModeTimedBtn to ClickIndex
	index ModeBoostBtn to ClickIndex
	index ModeOnBtn to ClickIndex
	index ModeOffBtn to ClickIndex
	gosub to ResetModeBtn
	if BoostState is `active` gosub to ActivateModeBoost
	else if Tmode is `Timed` gosub to ActivateModeTimed
	else if Tmode is `On` gosub to ActivateModeOn
	else gosub to ActivateModeOff

!	Target tile.
	index TargetBlockEl to ClickIndex
	index TargetValueEl to ClickIndex
	put `none` into TargetVis
	if BoostState is `active` put `block` into TargetVis
	else if BoostState is `configuring` put `block` into TargetVis
	else if Tmode is `On` put `block` into TargetVis
	set style `display` of TargetBlockEl to TargetVis
	if TargetVis is `block`
	begin
		if Ttarget is empty set the content of TargetValueEl to `20.0`
		else set the content of TargetValueEl to Ttarget
	end

!	Advance row — only in Timed (and not when the Boost panel has taken
!	the slot via Configuring). Hidden entirely when no schedule is in
!	view (nextTime empty) AND Advance is `-`, since there's nothing to
!	skip to; still shown when Advance is already `A` so the user can
!	cancel.
	index AdvanceBlockEl to ClickIndex
	if Tmode is `Timed`
	begin
		if BoostState is `configuring` set style `display` of AdvanceBlockEl to `none`
		else
		begin
			put property `advance` of Room into Advance
			if Advance is empty put `-` into Advance
			put property `nextTime` of Room into AdvanceNextTime
			if Advance is `-`
			begin
				if AdvanceNextTime is empty set style `display` of AdvanceBlockEl to `none`
				else set style `display` of AdvanceBlockEl to `block`
			end
			else set style `display` of AdvanceBlockEl to `block`
			index AdvanceBtn to ClickIndex
			gosub to PaintAdvanceBtn
		end
	end
	else set style `display` of AdvanceBlockEl to `none`

!	Boost row — visible in active or configuring. The Off button is the
!	"cancel" affordance: lit while configuring (no commit yet); active
!	state shows no duration lit (the duration buttons act as
!	"replace duration" while a boost is running, the Off button cancels).
	index BoostBlockEl to ClickIndex
	if BoostState is `none` set style `display` of BoostBlockEl to `none`
	else
	begin
		set style `display` of BoostBlockEl to `block`
		index BoostOffBtn to ClickIndex
		index Boost30Btn to ClickIndex
		index Boost1hBtn to ClickIndex
		index Boost2hBtn to ClickIndex
		gosub to ResetBoostBtn
		if BoostState is `configuring` gosub to ActivateBoostOff
	end
	return
!! @hash bbbbe071
!!!
!! Mode-button and boost-button styling helpers. Reset routines blank every button's selected look; Activate<X> routines apply the "lit" look (card background, drop shadow, primary text, weight 600) to one specific button. The buttons are already at the right slot via the `index` calls in PaintExpansion.
!!
!! ResetBoostBtn / ActivateBoost30 / Activate1h / Activate2h follow the same pattern but use accent-coloured borders rather than drop shadows because the boost row is the only place where multiple buttons can compete to be lit.
ResetModeBtn:
	set style `background` of ModeTimedBtn to `transparent`
	set style `color` of ModeTimedBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeTimedBtn to `500`
	set style `box-shadow` of ModeTimedBtn to `none`
	set style `background` of ModeBoostBtn to `transparent`
	set style `color` of ModeBoostBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeBoostBtn to `500`
	set style `box-shadow` of ModeBoostBtn to `none`
	set style `background` of ModeOnBtn to `transparent`
	set style `color` of ModeOnBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeOnBtn to `500`
	set style `box-shadow` of ModeOnBtn to `none`
	set style `background` of ModeOffBtn to `transparent`
	set style `color` of ModeOffBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeOffBtn to `500`
	set style `box-shadow` of ModeOffBtn to `none`
	return

ActivateModeTimed:
	set style `background` of ModeTimedBtn to `var(--color-surface-card)`
	set style `color` of ModeTimedBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeTimedBtn to `600`
	set style `box-shadow` of ModeTimedBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateModeBoost:
	set style `background` of ModeBoostBtn to `var(--color-surface-card)`
	set style `color` of ModeBoostBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeBoostBtn to `600`
	set style `box-shadow` of ModeBoostBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateModeOn:
	set style `background` of ModeOnBtn to `var(--color-surface-card)`
	set style `color` of ModeOnBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeOnBtn to `600`
	set style `box-shadow` of ModeOnBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateModeOff:
	set style `background` of ModeOffBtn to `var(--color-surface-card)`
	set style `color` of ModeOffBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeOffBtn to `600`
	set style `box-shadow` of ModeOffBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ResetBoostBtn:
	set style `background` of BoostOffBtn to `var(--color-surface-card)`
	set style `border` of BoostOffBtn to `1px solid var(--color-border-hairline)`
	set style `color` of BoostOffBtn to `var(--color-text-primary)`
	set style `font-weight` of BoostOffBtn to `500`
	set style `background` of Boost30Btn to `var(--color-surface-card)`
	set style `border` of Boost30Btn to `1px solid var(--color-border-hairline)`
	set style `color` of Boost30Btn to `var(--color-text-primary)`
	set style `font-weight` of Boost30Btn to `500`
	set style `background` of Boost1hBtn to `var(--color-surface-card)`
	set style `border` of Boost1hBtn to `1px solid var(--color-border-hairline)`
	set style `color` of Boost1hBtn to `var(--color-text-primary)`
	set style `font-weight` of Boost1hBtn to `500`
	set style `background` of Boost2hBtn to `var(--color-surface-card)`
	set style `border` of Boost2hBtn to `1px solid var(--color-border-hairline)`
	set style `color` of Boost2hBtn to `var(--color-text-primary)`
	set style `font-weight` of Boost2hBtn to `500`
	return

ActivateBoostOff:
	set style `background` of BoostOffBtn to `var(--color-accent-10)`
	set style `border` of BoostOffBtn to `1.5px solid var(--color-accent)`
	set style `color` of BoostOffBtn to `var(--color-accent)`
	set style `font-weight` of BoostOffBtn to `600`
	return

ActivateBoost30:
	set style `background` of Boost30Btn to `var(--color-accent-10)`
	set style `border` of Boost30Btn to `1.5px solid var(--color-accent)`
	set style `color` of Boost30Btn to `var(--color-accent)`
	set style `font-weight` of Boost30Btn to `600`
	return

ActivateBoost1h:
	set style `background` of Boost1hBtn to `var(--color-accent-10)`
	set style `border` of Boost1hBtn to `1.5px solid var(--color-accent)`
	set style `color` of Boost1hBtn to `var(--color-accent)`
	set style `font-weight` of Boost1hBtn to `600`
	return

ActivateBoost2h:
	set style `background` of Boost2hBtn to `var(--color-accent-10)`
	set style `border` of Boost2hBtn to `1.5px solid var(--color-accent)`
	set style `color` of Boost2hBtn to `var(--color-accent)`
	set style `font-weight` of Boost2hBtn to `600`
	return
!! @hash dd06764c
!!!
!! Open the Boost-configuring panel for the current row. No controller traffic — purely UI state.
!!
!! If the room is already in Boost mode (active), this is a no-op — the panel is already shown by PaintExpansion. Otherwise just flips on the configuring state and repaints; the target tile picks up Room.target via PaintExpansion (Boost and On share a single target).
OpenBoostPanel:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	if Tmode is `Boost` return
	put ClickIndex into BoostPanelOpenIndex
	gosub to PaintExpansion
	return
!! @hash dd45da46
!!!
!! Switch the current room into NewMode. Always clears any active boost (an explicit mode pick is a stronger signal than a transient boost) and any in-flight Boost-configuring panel state.
!!
!! Target is preserved across all mode changes — Off rooms keep their target so the user can still adjust it before applying a Boost. If the same mode is tapped twice with no Boost-panel open, we no-op.
!!
!! Leaving Boost mode: drops the bookkeeping that was tracking the active boost (boostRemaining, prevMode) locally, then ships an "Operating Mode" uirequest with the new mode and an explicit `Boost: 0` so the controller drops its own boost state. The cancel-boost message goes via the same payload rather than a separate CancelBoost path.
!!
!! For `On` mode the payload carries the room's target so the controller knows what setpoint to hold. For `Timed` an explicit `Boost: 0` is sent to clear any controller-side boost. SyncCurrentRoomToMap mirrors the change into the local Map copy so subsequent Save handlers don't revert it.
ChangeMode:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode

!	Close any open Boost-configuring panel for this row first. Tapping a
!	mode pill (any of them) is a stronger signal than the half-open panel.
	clear PanelWasOpen
	if BoostPanelOpenIndex is ClickIndex
	begin
		put -1 into BoostPanelOpenIndex
		set PanelWasOpen
	end

	if Tmode is NewMode
	begin
!		Same mode tapped — only do work if we just closed the panel.
		if PanelWasOpen gosub to PaintExpansion
		return
	end

!	Leaving Boost mode: drop the bookkeeping that was tracking the active
!	boost. The cancel-boost message goes via the standard ChangeMode
!	"Operating Mode" payload (Mode=<new>, Boost=0 for Timed).
	if Tmode is `Boost`
	begin
		set property `boostRemaining` of Room to 0
		set property `prevMode` of Room to empty
	end

	set property `mode` of Room to NewMode
	set property `boost` of Room to empty
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange
	gosub to SyncCurrentRoomToMap
	if Tmode is `Boost`
	begin
		put 0 into SyncBoostUntil
		gosub to SyncCurrentRoomBoostUntil
	end

	put NewMode into Mode
	gosub to LowercaseModeForServer
	put property `name` of Room into RoomNameForServer
	put property `target` of Room into TargetForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to ModeForServer
	if NewMode is `Timed` set property `Boost` of Result to 0
	else if NewMode is `On`
	begin
		set property `advance` of Result to `none`
		set property `target` of Result to TargetForServer
	end
!	Leaving Boost (any direction) — explicitly tell the controller to drop
!	its boost state, mirroring the old CancelBoost path's `Boost: 0`.
	if Tmode is `Boost` set property `Boost` of Result to 0
	gosub to PostUiRequest
	return
!! @hash fea795ee
!!!
!! Target steppers. StepTargetUp / StepTargetDown adjust by 0.5° (= 5 tenths) per tap, clamped to [50, 300] (= 5.0° to 30.0°). LoadTargetTenths reads Room.target into TargetT; WriteTargetTenths persists it back to Room.target and ships an "Operating Mode" with the current mode + new target. Boost-active edits additionally resend the boost duration so the controller's `until` is preserved.
!!
!! Boost-configuring and On share Room.target — there's no separate working copy, so every tap is a real commit regardless of which mode the user is in when they adjust the value. A user who bumps the target inside the Boost panel and then cancels the duration keeps the new target, same as if they'd been in On mode.
!!
!! A bare mode=boost message with no boost field would cause the controller to re-derive `until = now`, expiring the boost immediately — hence the explicit resend of the duration during active-boost target edits.
StepTargetUp:
	gosub to LoadTargetTenths
	add 5 to TargetT
	if TargetT is greater than 300 return
	gosub to WriteTargetTenths
	return

StepTargetDown:
	gosub to LoadTargetTenths
	take 5 from TargetT
	if TargetT is less than 50 return
	gosub to WriteTargetTenths
	return

!	Target source for the +/- step buttons. Always reads Room.target
!	(Boost and On share the same target).
LoadTargetTenths:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	put property `target` of Room into Ttarget
	if Ttarget is empty put `20.0` into Ttarget
	put Ttarget into TempStr
	gosub to ToTenths
	put TempTenths into TargetT
	return

!	Target step persisted. Two cases:
!	  - Boost active: persist target + resend the boost duration so the
!	    controller's `until` is preserved (a bare mode=boost with no boost
!	    field re-derives until = now → boost expires immediately).
!	  - Otherwise (On, Timed, Off, Boost-configuring): send "Operating
!	    Mode" with the unchanged mode + new target. Controller decides
!	    whether to use it now (On) or store it for later (Timed/Off).
WriteTargetTenths:
	put TargetT into TempTenths
	gosub to TenthsToString
	put property `mode` of Room into Tmode
	set property `target` of Room to TempStr
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange
	gosub to SyncCurrentRoomToMap

	put property `mode` of Room into Mode
	gosub to LowercaseModeForServer
	put property `name` of Room into RoomNameForServer
	put property `target` of Room into TargetForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to ModeForServer
	set property `target` of Result to TargetForServer
	if Tmode is `Boost`
	begin
		put property `boostRemaining` of Room into BoostMinutes
		if BoostMinutes is empty put 1 into BoostMinutes
		else if BoostMinutes is less than 1 put 1 into BoostMinutes
		set property `boost` of Result to `B` cat BoostMinutes
	end
	gosub to PostUiRequest
	return
!! @hash 936acece
!!!
!! Commit a Boost. The user has tapped a duration button (30 min / 1 hr / 2 hr) inside the configuring panel, or while a boost is already active (to replace the running duration).
!!
!! Promotes Room.mode to "Boost", captures the underlying mode as prevMode (so SyncCurrentRoomToMap can mirror it back to the controller's `prevmode` field), clears the panel state, then ships an "Operating Mode" uirequest with mode=boost, boost=B<minutes>, advance=none, target=Room.target. The target is whatever Room.target was before — Boost and On share it, and target +/- edits during configuring have already committed it.
!!
!! The controller stores its own `prevmode` based on its mode at message-receive time, but we still send a local prevMode mirror so that SyncCurrentRoomToMap keeps the local Map.profiles consistent with the controller's view.
ApplyBoost:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	if Tmode is not `Boost` set property `prevMode` of Room to Tmode

	put 0 into BoostMinutes
	if BoostDur is `30 min` put 30 into BoostMinutes
	else if BoostDur is `1 hr` put 60 into BoostMinutes
	else if BoostDur is `2 hr` put 120 into BoostMinutes

	set property `mode` of Room to `Boost`
	set property `boostRemaining` of Room to BoostMinutes
	if BoostMinutes is 1 set property `boost` of Room to `1 min`
	else set property `boost` of Room to BoostMinutes cat ` mins`
	put BoostMinutes into SyncBoostUntil
	multiply SyncBoostUntil by 60000
	add now to SyncBoostUntil
	set property `boostUntilMs` of Room to SyncBoostUntil
	set element ClickIndex of RoomsList to Room

	put -1 into BoostPanelOpenIndex

	gosub to AfterStateChange
	gosub to SyncCurrentRoomToMap
	gosub to SyncCurrentRoomBoostUntil

	put property `name` of Room into RoomNameForServer
	put property `target` of Room into TargetForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to `boost`
	set property `advance` of Result to `none`
	set property `boost` of Result to `B` cat BoostMinutes
	set property `target` of Result to TargetForServer
	gosub to PostUiRequest
	return
!! @hash 9f654a69
!!!
!! The Boost panel's "Off" duration button. Two cases:
!!
!! Configuring (panel open, mode != Boost): just close the panel. No controller traffic — any target edits the user made are already committed (Boost and On share Room.target, edits ship eagerly).
!!
!! Active (mode == Boost): cancel the boost. Locally revert mode to prevMode, clear boost text / boostRemaining / prevMode, and ship a cancel "Operating Mode" uirequest with mode=<prev>, Boost=0. The controller's stale `until` is harmless because expiration only fires when the controller's own mode is `boost` — once mode is back to the underlying value, `until` is ignored.
BoostOffTapped:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	if Tmode is not `Boost`
	begin
		if BoostPanelOpenIndex is ClickIndex
		begin
			put -1 into BoostPanelOpenIndex
			gosub to PaintExpansion
		end
		return
	end

	put property `prevMode` of Room into PrevMode
	if PrevMode is empty put `Off` into PrevMode
	set property `mode` of Room to PrevMode
	set property `boost` of Room to empty
	set property `boostRemaining` of Room to 0
	set property `prevMode` of Room to empty
	set element ClickIndex of RoomsList to Room

	gosub to AfterStateChange
	gosub to SyncCurrentRoomToMap
	put 0 into SyncBoostUntil
	gosub to SyncCurrentRoomBoostUntil

	put property `name` of Room into RoomNameForServer
	put PrevMode into Mode
	gosub to LowercaseModeForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to ModeForServer
	set property `Boost` of Result to 0
	gosub to PostUiRequest
	return
!! @hash 6518b52f
!!!
!! Toggle the Advance state for the current room. Optimistic local flip, then ship the new desired state in an "Operating Mode" uirequest.
!!
!! The controller treats any non-empty `advance` field on a `timed` mode command as a toggle, so sending the new state value moves it to that state regardless of how the controller currently sees it. The next map refresh reconciles.
!!
!! AdvanceBtn must already be indexed to ClickIndex (the click handler in WireRoomInteractions ensures this).
ToggleAdvance:
	put element ClickIndex of RoomsList into Room
	put property `advance` of Room into Advance
	if Advance is empty put `-` into Advance
	if Advance is `A` put `-` into Advance
	else put `A` into Advance
	set property `advance` of Room to Advance
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange

	gosub to SyncCurrentRoomToMap

	put property `name` of Room into RoomNameForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to `timed`
	set property `advance` of Result to Advance
	gosub to PostUiRequest
	return
!! @hash e3009772
!!!
!! Mirror the locally-mutated Room (RoomsList[ClickIndex]) back into Map.profiles[CurrentProfile].rooms[legacyIdx], translating new-UI fields (Title-case mode, Boost-as-peer-mode overlay) into the legacy controller form.
!!
!! Called after every per-room state change so any subsequent Save that ships `Update Profiles` (Outside, System, Profile, Schedule, Devices) carries fresh data and doesn't accidentally revert the per-room toggle the user just made.
!!
!! Mode translation: Title-case → lowercase. When the new-UI mode is "Boost", the legacy mode is `boost` and `prevmode` carries the lowercase underlying mode (held on Room.prevMode). Otherwise a straight Title→lower mapping with `prevmode` left alone (the controller manages it).
!!
!! Boost-specific `until` is handled separately by SyncCurrentRoomBoostUntil so the timestamp can be cleared on cancel without going through the mode-mapping logic.
SyncCurrentRoomToMap:
	put property `legacyIdx` of Room into SyncLegacyIdx
	put property `profiles` of Map into SyncProfiles
	put element CurrentProfile of SyncProfiles into SyncProfile
	put property `rooms` of SyncProfile into SyncRooms
	put element SyncLegacyIdx of SyncRooms into SyncLegacyRoom

	set property `advance` of SyncLegacyRoom to property `advance` of Room
	set property `target` of SyncLegacyRoom to property `target` of Room

!	Mode: title-case → lowercase. When the new-UI mode is "Boost", the
!	legacy mode is `boost` and `prevmode` carries the lowercase underlying
!	mode (held on Room.prevMode). Otherwise it's a straight title→lower
!	mapping with `prevmode` left alone (the controller manages it).
	put property `mode` of Room into SyncUiMode
	if SyncUiMode is `Boost`
	begin
		set property `mode` of SyncLegacyRoom to `boost`
		put property `prevMode` of Room into SyncBaseMode
		put `off` into SyncPrevModeLegacy
		if SyncBaseMode is `Timed` put `timed` into SyncPrevModeLegacy
		else if SyncBaseMode is `On` put `on` into SyncPrevModeLegacy
		set property `prevmode` of SyncLegacyRoom to SyncPrevModeLegacy
	end
	else
	begin
		put `off` into SyncBaseMode
		if SyncUiMode is `Timed` put `timed` into SyncBaseMode
		else if SyncUiMode is `On` put `on` into SyncBaseMode
		set property `mode` of SyncLegacyRoom to SyncBaseMode
	end

	set element SyncLegacyIdx of SyncRooms to SyncLegacyRoom
	set property `rooms` of SyncProfile to SyncRooms
	set element CurrentProfile of SyncProfiles to SyncProfile
	set property `profiles` of Map to SyncProfiles
	return
!! @hash d089d1f6
!!!
!! Write SyncBoostUntil (the boost-expiry timestamp, or 0 on cancel) onto the current room's legacy slot in Map.profiles. Called by ApplyBoost (with a future timestamp), ChangeMode and BoostOffTapped (with 0 to clear).
!!
!! Mirrors the controller's own boost setup: timestamp = now + minutes × 60000.
SyncCurrentRoomBoostUntil:
	put property `legacyIdx` of Room into SyncLegacyIdx
	put property `profiles` of Map into SyncProfiles
	put element CurrentProfile of SyncProfiles into SyncProfile
	put property `rooms` of SyncProfile into SyncRooms
	put element SyncLegacyIdx of SyncRooms into SyncLegacyRoom
	set property `until` of SyncLegacyRoom to SyncBoostUntil
	set element SyncLegacyIdx of SyncRooms to SyncLegacyRoom
	set property `rooms` of SyncProfile to SyncRooms
	set element CurrentProfile of SyncProfiles to SyncProfile
	set property `profiles` of Map to SyncProfiles
	return
!! @hash 0991d205
!!!
!! Style the Advance button for the current Advance value. Active state ("Cancel the advance") gets the accent-tinted treatment; inactive state ("Advance to next schedule period (HH:MM)") gets the plain card surface. Reads the Advance and AdvanceNextTime globals; caller must `index AdvanceBtn to ClickIndex` first.
!!
!! AdvanceNextTime is the HH:MM the system would skip to when Advance is engaged from the current state — sourced from Room.nextTime by PaintExpansion, which has the live projection. After a local toggle the projection becomes stale for ~10s until the next map push reconciles, but the inactive→active flip hides the time in the label so the user doesn't see the stale value.
PaintAdvanceBtn:
	if Advance is `A`
	begin
		set the content of AdvanceBtn to `Cancel the advance`
		set style `background` of AdvanceBtn to `var(--color-accent-10)`
		set style `border` of AdvanceBtn to `1.5px solid var(--color-accent)`
		set style `color` of AdvanceBtn to `var(--color-accent)`
		set style `font-weight` of AdvanceBtn to `600`
	end
	else
	begin
		if AdvanceNextTime is empty
			set the content of AdvanceBtn to `Advance to next schedule period`
		else set the content of AdvanceBtn to `Advance to next schedule period (` cat AdvanceNextTime cat `)`
		set style `background` of AdvanceBtn to `var(--color-surface-card)`
		set style `border` of AdvanceBtn to `1px solid var(--color-border-hairline)`
		set style `color` of AdvanceBtn to `var(--color-text-primary)`
		set style `font-weight` of AdvanceBtn to `500`
	end
	return
!! @hash f222c162
!!!
!! Lowercase the Title-case Mode (Timed/On/Off/Boost) into ModeForServer (timed/on/off/boost) for the controller's payload format. Reads the global Mode variable in, writes ModeForServer out — callers must `put <newmode> into Mode` first.
LowercaseModeForServer:
	put `off` into ModeForServer
	if Mode is `Timed` put `timed` into ModeForServer
	else if Mode is `On` put `on` into ModeForServer
	else if Mode is `Boost` put `boost` into ModeForServer
	return
!! @hash 51017bf2
!!!
!! Open the combined ProfileSheet via the profile-sheet.as module. Ships the current profiles snapshot + active profile name + calendar state and parks on the reply.
!!
!! The module returns either `{cancelled: yes}` (Cancel) or `{cancelled: no, profiles, activeIdx, calendarOn, calendarData}` (Save). On a save we ship the full Update Profiles via SendUpdateProfiles. The active idx may have changed (rename of active profile, or explicit row selection), so we use whatever the module computed rather than CurrentProfile.
OpenProfileSheet:
	put `{}` into OpenMsg
	set property `profiles` of OpenMsg to property `profiles` of Map
	set property `activeProfileName` of OpenMsg to ActiveProfileName
	if CalendarOn set property `calendarOn` of OpenMsg to `on`
	else set property `calendarOn` of OpenMsg to `off`
	set property `calendarData` of OpenMsg to property `calendar-data` of Map
	gosub to HideAllSheets
	set the content of SheetTitleEl to `Profile`
	gosub to OpenSheet
	send OpenMsg to ProfileSheetModule and assign reply to ProfileResult
	gosub to CloseSheet
	if property `cancelled` of ProfileResult is `no`
	begin
		put property `profiles` of ProfileResult into PayloadProfiles
		put property `activeIdx` of ProfileResult into PayloadActiveProfileIdx
		if property `calendarOn` of ProfileResult is `on` set PayloadCalendarOnFlag
		else clear PayloadCalendarOnFlag
		put property `calendarData` of ProfileResult into PayloadCalendarData
		gosub to SendUpdateProfiles
	end
	return
!! @hash ece45f8c
!!!
!! Open the schedule editor for the room at ClickIndex. The schedule-editor.as module owns the sheet's DOM and logic; we just ship the open-payload and park on the reply.
!!
!! Snapshot the current Map state (profiles + active profile index), build the open dict, open the sheet chrome with the room's title, then send-and-block. The module renders its own period cards, runs its own event loop until the user clicks Save or Cancel, and ships back `{cancelled: yes|no, profiles}`. On a Save reply we ship the resulting Update Profiles via SendUpdateProfiles. CloseSheet animates the chrome closed in either case.
OpenScheduleEditor:
	put element ClickIndex of RoomsList into Room
	put `{}` into OpenMsg
	set property `roomName` of OpenMsg to property `name` of Room
	set property `roomLegacyIdx` of OpenMsg to property `legacyIdx` of Room
	set property `profileIdx` of OpenMsg to CurrentProfile
	set property `profiles` of OpenMsg to property `profiles` of Map
	gosub to HideAllSheets
	set the content of SheetTitleEl to `Schedule for ` cat property `name` of Room
	gosub to OpenSheet
	send OpenMsg to ScheduleEditorModule and assign reply to ScheduleResult
	gosub to CloseSheet
	if property `cancelled` of ScheduleResult is `no`
	begin
		put property `profiles` of ScheduleResult into PayloadProfiles
		put CurrentProfile into PayloadActiveProfileIdx
		if CalendarOn set PayloadCalendarOnFlag else clear PayloadCalendarOnFlag
		put property `calendar-data` of Map into PayloadCalendarData
		gosub to SendUpdateProfiles
	end
	return
!! @hash 9fdc73c7
!!!
!! Open the read-only room-info sheet for the room at ClickIndex. Shows the current readings (relay, temperature, humidity, battery, last-report age) and stays open across map refreshes — RefreshHomeScreen detects InfoSheetOpen and calls PaintInfoSheet to update the values in place.
OpenInfoSheet:
	put ClickIndex into InfoSheetRoomIdx
	put element InfoSheetRoomIdx of RoomsList into Room
	gosub to PaintInfoSheet
	gosub to HideAllSheets
	set style `display` of InfoSheetEl to `block`
	set the content of SheetTitleEl to property `name` of Room
	set InfoSheetOpen
	gosub to OpenSheet
	return
!! @hash 413b2fe9
!!!
!! Close the info sheet and clear InfoSheetOpen so RefreshHomeScreen stops repainting it.
CloseInfoSheet:
	clear InfoSheetOpen
	gosub to CloseSheet
	return
!! @hash f9d3ecc3
!!!
!! Format the readings for the open info sheet. Each value falls back to `—` when the data isn't available (sensor never reported, no humidity channel, battery not yet known, etc).
!!
!! Age is formatted from `sensorAge` (milliseconds since last report) as "<1 min ago", "1 min ago", or "N min ago". Caller must have set Room to the room being displayed.
PaintInfoSheet:
	put property `relay` of Room into InfoRelayVal
	if InfoRelayVal is `on` set the content of InfoRelayValue to `On`
	else if InfoRelayVal is `off` set the content of InfoRelayValue to `Off`
	else set the content of InfoRelayValue to `—`

	put property `temp` of Room into TempStr
	if TempStr is empty set the content of InfoTempValue to `—`
	else set the content of InfoTempValue to TempStr cat `°C`

	put property `humidity` of Room into InfoHumidityVal
	if InfoHumidityVal is empty set the content of InfoHumidityValue to `—`
	else set the content of InfoHumidityValue to `` cat InfoHumidityVal cat `%`

	put property `battery` of Room into InfoBatteryVal
	if InfoBatteryVal is empty set the content of InfoBatteryValue to `—`
	else if InfoBatteryVal is 0 set the content of InfoBatteryValue to `—`
	else set the content of InfoBatteryValue to `` cat InfoBatteryVal cat `%`

	put property `sensorAge` of Room into InfoAgeMs
	if InfoAgeMs is empty set the content of InfoAgeValue to `—`
	else
	begin
		put InfoAgeMs into InfoAgeMin
		divide InfoAgeMin by 60000
		if InfoAgeMin is less than 1 set the content of InfoAgeValue to `<1 min ago`
		else if InfoAgeMin is 1 set the content of InfoAgeValue to `1 min ago`
		else set the content of InfoAgeValue to `` cat InfoAgeMin cat ` min ago`
	end
	return
!! @hash dcb3ec9a
!!!
!! Open the system type & name sheet from the menu's "System" row.
!!
!! Snapshots SystemName and SystemType into the Editing* vars, paints the type-pill highlight, swaps the visible sheet. The controller's existing System Name handler picks up `name`; `systemType` is included as an additional map-root field that the controller currently just preserves, ready for future fuel-aware logic (Boiler vs Heat Pump scheduling differs in optimisation targets).
OpenSystemSheet:
	put SystemName into EditingSystemName
	put SystemType into EditingSystemType
	if EditingSystemType is empty put `Boiler` into EditingSystemType
	set the content of SystemSheetName to EditingSystemName
	gosub to PaintSystemSheetType
	gosub to HideAllSheets
	set style `display` of SystemSheetEl to `block`
	set the content of SheetTitleEl to `System type & name`
	gosub to OpenSheet
	return
!! @hash e11582d7
!!!
!! Paint and activation helpers for the Boiler / Heat Pump type pill. Reset blanks both pills; Activate<X> applies the lit look (card background, drop shadow, weight 600) to the matching pill.
PaintSystemSheetType:
	gosub to ResetSystemSheetTypeBtns
	if EditingSystemType is `Boiler` gosub to ActivateSystemTypeBoiler
	else if EditingSystemType is `Heat Pump` gosub to ActivateSystemTypeHeatPump
	return

ResetSystemSheetTypeBtns:
	set style `background` of SystemSheetTypeBoiler to `transparent`
	set style `color` of SystemSheetTypeBoiler to `var(--color-text-muted)`
	set style `font-weight` of SystemSheetTypeBoiler to `500`
	set style `box-shadow` of SystemSheetTypeBoiler to `none`
	set style `background` of SystemSheetTypeHeatPump to `transparent`
	set style `color` of SystemSheetTypeHeatPump to `var(--color-text-muted)`
	set style `font-weight` of SystemSheetTypeHeatPump to `500`
	set style `box-shadow` of SystemSheetTypeHeatPump to `none`
	return

ActivateSystemTypeBoiler:
	set style `background` of SystemSheetTypeBoiler to `var(--color-surface-card)`
	set style `color` of SystemSheetTypeBoiler to `var(--color-text-primary)`
	set style `font-weight` of SystemSheetTypeBoiler to `600`
	set style `box-shadow` of SystemSheetTypeBoiler to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateSystemTypeHeatPump:
	set style `background` of SystemSheetTypeHeatPump to `var(--color-surface-card)`
	set style `color` of SystemSheetTypeHeatPump to `var(--color-text-primary)`
	set style `font-weight` of SystemSheetTypeHeatPump to `600`
	set style `box-shadow` of SystemSheetTypeHeatPump to `0 1px 3px rgba(0,0,0,0.08)`
	return
!! @hash f78e46ed
!!!
!! Save the system type & name edits. Writes the new fields into Map locally, refreshes the summary, then ships a single `System Name` uirequest carrying both `name` and `systemType` as map-root fields.
SaveSystemSheet:
	put the content of SystemSheetName into EditingSystemName
	set property `name` of Map to EditingSystemName
	set property `systemType` of Map to EditingSystemType
	put EditingSystemName into SystemName
	put EditingSystemType into SystemType
	gosub to PaintSummary

	put `{}` into Result
	set property `Action` of Result to `System Name`
	set property `name` of Result to EditingSystemName
	set property `systemType` of Result to EditingSystemType
	gosub to PostUiRequest
	gosub to CloseSheet
	return
!! @hash 68cd9583
!!!
!! Open the Outside thermometer + frost protection sheet from the menu's Outside row.
!!
!! The outside thermometer lives in the legacy "room with empty relays" slot of every profile. Its `sensor` and `ptemp` fields are fanned out across every profile on save so the controller sees the same outdoor config regardless of which profile is active. FrostActive (used by the summary card) is derived per refresh from the controller's `frostActive` flag if present, else computed locally (outside temp ≤ trigger AND no rooms calling).
!!
!! Snapshots the current OutsideSensor / FrostTrigger into the Editing* vars, sets the input contents, swaps the visible sheet.
OpenOutsideSheet:
	put OutsideSensor into EditingOutsideSensor
	put FrostTrigger into EditingFrostTrigger
	set the content of OutsideSheetSensor to EditingOutsideSensor
	set the content of OutsideSheetFrost to EditingFrostTrigger
	gosub to HideAllSheets
	set style `display` of OutsideSheetEl to `block`
	set the content of SheetTitleEl to `Outside thermometer`
	gosub to OpenSheet
	return
!! @hash 49a64a64
!!!
!! Save the outside-sensor edits. Read the inputs, fan the sensor name + ptemp/protect fields across every profile's outside-room slot in the local Map, ship a full `Update Profiles` uirequest, then update the local OutsideSensor / FrostTrigger mirrors.
!!
!! If no outside room exists in the map yet (controller never registered one) the save is aborted with an alert — the controller would need to add the slot first, which isn't a UI flow yet.
!!
!! An empty FrostTrigger means "frost protection off" — sets `protect: no` and clears `ptemp`. Any non-empty value sets `protect: yes` and writes the trigger temperature.
SaveOutsideSheet:
	if not OutsideRoomFound
	begin
		alert `No outside-thermometer slot found in the map. The controller needs to add one first.`
		return
	end
	put the content of OutsideSheetSensor into EditingOutsideSensor
	put the content of OutsideSheetFrost into EditingFrostTrigger

	put property `profiles` of Map into LiveProfiles
	put the json count of LiveProfiles into DeviceProfileCount
	put 0 into OutsideProfileLoopI
	while OutsideProfileLoopI is less than DeviceProfileCount
	begin
		put element OutsideProfileLoopI of LiveProfiles into LiveProfileForOutside
		put property `rooms` of LiveProfileForOutside into LiveRoomsForOutside
		put element OutsideRoomLegacyIdx of LiveRoomsForOutside into LiveRoomForOutside
		set property `sensor` of LiveRoomForOutside to EditingOutsideSensor
		if EditingFrostTrigger is empty
		begin
			set property `protect` of LiveRoomForOutside to `no`
			set property `ptemp` of LiveRoomForOutside to empty
		end
		else
		begin
			set property `protect` of LiveRoomForOutside to `yes`
			set property `ptemp` of LiveRoomForOutside to EditingFrostTrigger
		end
		set element OutsideRoomLegacyIdx of LiveRoomsForOutside to LiveRoomForOutside
		set property `rooms` of LiveProfileForOutside to LiveRoomsForOutside
		set element OutsideProfileLoopI of LiveProfiles to LiveProfileForOutside
		increment OutsideProfileLoopI
	end

	put LiveProfiles into PayloadProfiles
	put CurrentProfile into PayloadActiveProfileIdx
	if CalendarOn set PayloadCalendarOnFlag else clear PayloadCalendarOnFlag
	put property `calendar-data` of Map into PayloadCalendarData
	gosub to SendUpdateProfiles

	put EditingOutsideSensor into OutsideSensor
	put EditingFrostTrigger into FrostTrigger
	gosub to CloseSheet
	return
!! @hash 4dda8018
!!!
!! Open the device editor for room + device configuration. The device-editor.as module owns the sheet's DOM and logic; we just ship the open-payload and park on the reply.
!!
!! Two outbound payloads on a non-cancelled save: Update Profiles for the room-list and per-room device-field changes, plus Request Relay (only when the demand-relay value actually changed). Module signals the latter via `requestRelayChanged: yes` in the reply.
!!
!! Aborts early with an alert if there are no rooms yet, or if Map.profiles is empty (shouldn't happen post-bootstrap, defensive check).
OpenDeviceEditor:
	if RoomCount is 0
	begin
		alert `No rooms in the system yet.`
		return
	end
	if property `profiles` of Map is empty
	begin
		log `OpenDeviceEditor: Map.profiles empty — aborting`
		alert `Map data not loaded — please reload the page.`
		return
	end
	put `{}` into OpenMsg
	set property `profiles` of OpenMsg to property `profiles` of Map
	set property `currentProfile` of OpenMsg to CurrentProfile
	set property `requestRelay` of OpenMsg to RequestRelay
	gosub to HideAllSheets
	set the content of SheetTitleEl to `Rooms and Devices`
	gosub to OpenSheet
	send OpenMsg to DeviceEditorModule and assign reply to DeviceResult
	gosub to CloseSheet
	if property `cancelled` of DeviceResult is `no`
	begin
		put property `profiles` of DeviceResult into PayloadProfiles
		put CurrentProfile into PayloadActiveProfileIdx
		if CalendarOn set PayloadCalendarOnFlag else clear PayloadCalendarOnFlag
		put property `calendar-data` of Map into PayloadCalendarData
		gosub to SendUpdateProfiles
		if property `requestRelayChanged` of DeviceResult is `yes`
		begin
			put property `requestRelay` of DeviceResult into RequestRelay
			set property `request` of Map to RequestRelay
			put `{}` into Result
			set property `Action` of Result to `Request Relay`
			set property `request` of Result to RequestRelay
			gosub to PostUiRequest
		end
	end
	return
!! @hash 1f636809
!!!
!! Panic-button handler for stranded credentials. Wipes the stored MAC and reloads — useful when a typo has stranded the page on connect.
!!
!! Broker / username / password now come from credentials.php so they're not in localStorage to clear. Older keys (dev-broker / dev-username / dev-password) from the prior four-prompt setup are also cleared, so an upgraded install ends up tidy. Wired to the hamburger button before BuildHomeScreen runs — once the menu sheet is built, the hamburger gets re-bound to open the menu.
ResetCredentialsAndReload:
	clear ConfirmFlag
	if confirm `Reset stored MAC and reload? You'll be prompted to re-enter it.` set ConfirmFlag
	if not ConfirmFlag return
	put empty into storage as `dev-broker`
	put empty into storage as `dev-username`
	put empty into storage as `dev-password`
	put empty into storage as `dev-mac`
	location the location
	return
!! @hash 80980e08
!!!
!! Open the About sheet. Auto-opened in demo mode (no credentials yet) so first-time visitors see what RBR is; otherwise reachable via tap-on-the-house-mark in the topbar at any time.
!!
!! The "Set up my system" CTA is only revealed in demo mode — existing users with credentials don't see a setup prompt that doesn't apply to them. Sheet defaults to the About tab; the Manual tab is selectable via the tab pills below the header.
OpenAboutSheet:
	gosub to HideAllSheets
	set style `display` of AboutSheetEl to `block`
	if DemoMode set style `display` of AboutCtaSetup to `block`
	else set style `display` of AboutCtaSetup to `none`
	gosub to ShowAboutTabAbout
	set the content of SheetTitleEl to `About`
	gosub to OpenSheet
	return
!! @hash 12cdf0fa
!!!
!! About-sheet tab swappers. Active tab pill gets the surface-card background + drop shadow + bold; inactive gets transparent. Body visibility follows.
ShowAboutTabAbout:
	set style `display` of AboutBodyAbout to `block`
	set style `display` of AboutBodyManual to `none`
	set style `background` of AboutTabAbout to `var(--color-surface-card)`
	set style `box-shadow` of AboutTabAbout to `0 1px 3px rgba(0,0,0,0.08)`
	set style `color` of AboutTabAbout to `var(--color-text-primary)`
	set style `font-weight` of AboutTabAbout to `600`
	set style `background` of AboutTabManual to `transparent`
	set style `box-shadow` of AboutTabManual to `none`
	set style `color` of AboutTabManual to `var(--color-text-muted)`
	set style `font-weight` of AboutTabManual to `500`
	return

ShowAboutTabManual:
	set style `display` of AboutBodyAbout to `none`
	set style `display` of AboutBodyManual to `block`
	set style `background` of AboutTabAbout to `transparent`
	set style `box-shadow` of AboutTabAbout to `none`
	set style `color` of AboutTabAbout to `var(--color-text-muted)`
	set style `font-weight` of AboutTabAbout to `500`
	set style `background` of AboutTabManual to `var(--color-surface-card)`
	set style `box-shadow` of AboutTabManual to `0 1px 3px rgba(0,0,0,0.08)`
	set style `color` of AboutTabManual to `var(--color-text-primary)`
	set style `font-weight` of AboutTabManual to `600`
	return
!! @hash c5aac8db
!!!
!! "Set up my system" CTA. Broker / username / password are now shared and fetched from credentials.php, so the only thing the user has to supply is the controller's MAC address. Stored in localStorage and picked up on the next page load via `location the location`.
SetupMySystem:
	put prompt `Enter your controller's MAC address` cat newline cat `(printed on the device, format aa:bb:cc:dd:ee:ff):` into MAC
	if MAC is empty return
	if MAC is `null` return
	if MAC is `undefined` return
	put MAC into storage as `dev-mac`
	location the location
	return
!! @hash 9ea89fc1
!!!
!! Ship the Result JSON object to the controller as a `uirequest`.
!!
!! Optimistic pattern: every caller has already mutated local state to reflect the change. On send failure we just bump a consecutive-failure counter; the next refresh will reconcile the controller's view (or the user can reload the page).
!!
!! Transient hiccups (suspended WebSocket, brief network blip) clear on their own as the poll loop reconnects. We only surface a user-facing alert once we've seen three consecutive failures, so the noise stays low. The alert reset is destructive (puts us back to 0) so the next batch of three failures will alert again.
!!
!! In demo mode (no controller configured) the send is a no-op — visitors can poke the UI without throwing errors.
PostUiRequest:
	if DemoMode return
	log `Sending uirequest: ` cat property `Action` of Result
	send to ServerTopic
		sender MyTopic
		action `uirequest`
		message Result
		giving SendOK
	if SendOK
	begin
		put 0 into ConsecutiveSendFailures
		return
	end
	log `WARNING: MQTT send failed (no broker acknowledgment)`
	increment ConsecutiveSendFailures
!	Only surface a user-facing alert once the failure looks persistent —
!	transient hiccups (suspended WebSocket, brief network blip) clear up
!	on their own as the poll loop reconnects. Three strikes = noisy.
	if ConsecutiveSendFailures is greater than 2
	begin
		alert `Connection problem. Please reload the page if this persists.`
		put 0 into ConsecutiveSendFailures
	end
	return
!! @hash 3e399f34
!!!
!! Build and ship an `Update Profiles` uirequest. Callers set the four Payload* inputs first: PayloadProfiles (the profiles array), PayloadActiveProfileIdx (the active profile index), PayloadCalendarOnFlag (set/cleared), and PayloadCalendarData (the calendar-data array, or empty to omit).
!!
!! Folds the four lines of skeleton + the calendar-on/off if + the calendar-data conditional into one gosub, avoiding the same payload-construction sequence in SaveScheduleEditor / SaveOutsideSheet / SaveDeviceEditor / SaveEditingProfiles.
SendUpdateProfiles:
	put `{}` into Result
	set property `Action` of Result to `Update Profiles`
	set property `profiles` of Result to PayloadProfiles
	set property `profile` of Result to PayloadActiveProfileIdx
	if PayloadCalendarOnFlag set property `calendar` of Result to `on`
	else set property `calendar` of Result to `off`
	if PayloadCalendarData is not empty set property `calendar-data` of Result to PayloadCalendarData
	gosub to PostUiRequest
	return
!! @hash 85af1368
!!!
!! Per-room post-change repaint. Called from every interactive change handler (ChangeMode, WriteTargetTenths, ApplyBoost, BoostOffTapped, ToggleAdvance) after the local Room dict has been mutated.
!!
!! Recomputes `calling` for this room, writes the updated Room back into RoomsList[ClickIndex], re-renders the rest row, repaints the expansion panel, and refreshes the summary card. Room and ClickIndex must be set on entry.
AfterStateChange:
	gosub to RecalcCalling
	set element ClickIndex of RoomsList to Room
	put ClickIndex into RoomIndex
	put `` cat RoomIndex into IndexStr
	gosub to RenderRoom
	gosub to PaintExpansion
	gosub to ComputeSummaryStats
	gosub to PaintSummary
	return
!! @hash eb6faa04
!!!
!! Recompute `calling` (the "this room wants heat right now" flag) for the current Room. Optimistic local update — the controller's authoritative answer follows on the next map push.
!!
!! A sensor (outdoor) row never calls. An offline room never calls. An online room can call when its mode is not Off — Boost is its own mode and always drives the relay until expiry; Off-with-an-active-boost is now mode == "Boost" with prevMode == "Off", so the single Mode-not-Off test covers both cases.
!!
!! Target source matters and varies by mode. On and Boost: controller targets Room.target (the held setpoint), so compare against that. Timed: controller targets the current period's temp when in-period or background-temp when in a gap — both already projected into Room.nextTarget by map-to-rooms. Using Room.target in Timed mode would falsely call for heat whenever the persistent setpoint exceeds background-temp, even when the controller's real comparison (temp vs background-temp) says the relay should stay off; that mismatch can persist for minutes because the controller, seeing no state change, only sends empty heartbeat pings rather than a fresh map.
!!
!! ComputeCallingDiff is the actual temp-vs-target compare: relay on when current < target with no hysteresis, matching the controller's SetRelay logic. Re-deriving in the UI keeps the summary card consistent with what the user just clicked, without waiting for the round trip.
RecalcCalling:
	put `no` into NewCalling
	put property `sensor` of Room into Tsensor
	put property `offline` of Room into Toffline
	put property `mode` of Room into Tmode
	put property `temp` of Room into Ttemp
	put property `target` of Room into Ttarget
	if Tmode is `Timed` put property `nextTarget` of Room into Ttarget
	if Tsensor is `no`
	begin
		if Toffline is `no`
		begin
			if Tmode is not `Off` gosub to ComputeCallingDiff
		end
	end
	set property `calling` of Room to NewCalling
	return
!! @hash 533fa1d3
!!!
!! Inner branch of RecalcCalling. Compares Ttemp to Ttarget (both as integer tenths via ToTenths) and flips NewCalling to `yes` if temp is below target. Mirrors the controller's SetRelay: relay on when TempNow < Target, no hysteresis.
ComputeCallingDiff:
	if Ttemp is empty return
	if Ttarget is empty return
	put Ttemp into TempStr
	gosub to ToTenths
	put TempTenths into TempT
	put Ttarget into TempStr
	gosub to ToTenths
	put TempTenths into TargetT
	take TempT from TargetT giving Diff
	if Diff is greater than 0 put `yes` into NewCalling
	return
!! @hash d04ce3fd
!!!
!! Walk RoomsList and recompute the SummaryCard aggregates. Sets HeatingCount, HeatingNames, AvgText, OutsideText, TitleText, SubtitleText — all consumed by PaintSummary.
!!
!! Average temperature is the mean of online rooms' temperatures, in tenths-of-a-degree internally to keep the integer arithmetic clean, then formatted as "X.Y°". OutsideTemp is owned by MapToRooms (extracted from the outdoor sensor entry which is filtered out of RoomsList) — we don't reset it here.
!!
!! Frost protection: trust the controller's `frostActive` flag if it sets one (the controller knows things the UI doesn't, like demand-relay state). Otherwise compute locally: active when a trigger is set, the outdoor temperature is at-or-below it, AND no rooms are calling.
!!
!! Title/subtitle picks one of four messages: "Frost protection active" (overrides everything), "Nothing calling for heat" (idle), "<Room> is calling for heat" (single), or "<N> rooms calling for heat" with comma-joined names (multi).
ComputeSummaryStats:
	put 0 into HeatingCount
	put empty into HeatingNames
	put 0 into SumTenths
	put 0 into AvgCount
!	OutsideTemp is owned by MapToRooms (extracted from the outdoor sensor
!	entry, which is filtered out of RoomsList). Don't reset it here.

	put 0 into LoopI
	while LoopI is less than RoomCount
	begin
		put element LoopI of RoomsList into CurRoom
		put property `name` of CurRoom into RName
		put property `temp` of CurRoom into Ttemp
		put property `offline` of CurRoom into Toffline
		put property `calling` of CurRoom into Tcalling

		if Tcalling is `yes`
		begin
			increment HeatingCount
			if HeatingNames is empty put RName into HeatingNames
			else put HeatingNames cat `, ` cat RName into HeatingNames
		end

		if Toffline is `no`
		begin
			if Ttemp is not empty
			begin
				put the index of `.` in Ttemp into DotIdx
				if DotIdx is less than 0
				begin
					put the value of Ttemp into TenthsOne
					multiply TenthsOne by 10
				end
				else
				begin
					put the value of left DotIdx of Ttemp into TenthsOne
					multiply TenthsOne by 10
					increment DotIdx
					put the value of from DotIdx of Ttemp into DecPart
					add DecPart to TenthsOne
				end
				add TenthsOne to SumTenths
				increment AvgCount
			end
		end

		increment LoopI
	end

	put `—` into AvgText
	if AvgCount is greater than 0
	begin
		divide SumTenths by AvgCount
		put SumTenths modulo 10 into AvgDec
		put SumTenths into AvgInt
		divide AvgInt by 10
		put AvgInt cat `.` cat AvgDec cat `°` into AvgText
	end

	put `—` into OutsideText
	if OutsideTemp is not empty put OutsideTemp cat `°` into OutsideText

!	Frost protection: trust the controller's `frostActive` flag if it sets
!	one, otherwise compute locally — active when a trigger is set, the
!	outdoor temperature is at-or-below it, and no rooms are calling.
	clear FrostActive
	if property `frostActive` of Map is `yes` set FrostActive
	else
	begin
		if FrostTrigger is not empty
		begin
			if OutsideTemp is not empty
			begin
				if HeatingCount is 0
				begin
					put OutsideTemp into TempStr
					gosub to ToTenths
					put TempTenths into OutsideTempTenths
					put FrostTrigger into TempStr
					gosub to ToTenths
					put TempTenths into FrostTriggerTenths
					if OutsideTempTenths is not greater than FrostTriggerTenths set FrostActive
				end
			end
		end
	end

	if FrostActive
	begin
		put `Frost protection active` into TitleText
		put `Demand relay firing` into SubtitleText
	end
	else if HeatingCount is 0
	begin
		put `Nothing calling for heat` into TitleText
		put `System idle` into SubtitleText
	end
	else if HeatingCount is 1
	begin
		put HeatingNames cat ` is calling for heat` into TitleText
		put `System firing` into SubtitleText
	end
	else
	begin
		put HeatingCount cat ` rooms calling for heat` into TitleText
		put HeatingNames into SubtitleText
	end
	return
!! @hash 37c33f16
!!!
!! Push the aggregates from ComputeSummaryStats into the SummaryCard DOM. Element vars must already be attached (BuildHomeScreen does this once at startup).
!!
!! Also refreshes today's date string, the active profile name, and the system ID — all of which depend on live data and so can't be set during synchronous startup. The frost-active badge in the outside row toggles inline-block vs none. The summary chip background/icon swap heat vs neutral based on HeatingCount.
PaintSummary:
	set the content of SummaryTitle to TitleText
	set the content of SummarySubtitle to SubtitleText
	set the content of SummaryAvg to AvgText
	set the content of SummaryOutside to OutsideText

	gosub to FormatTodayString
	set the content of SummaryToday to TempStr

	if ActiveProfileName is not empty
	begin
		put ActiveProfileName into ProfileName
		set the content of SummaryProfileName to ActiveProfileName
	end
	if SystemName is not empty set the content of SystemId to SystemName

	if FrostActive set style `display` of SummaryOutsideFrost to `inline-block`
	else set style `display` of SummaryOutsideFrost to `none`

	if HeatingCount is 0
	begin
		set style `background` of SummaryChip to `var(--color-chip-neutral-bg)`
		set style `background-color` of SummaryChipIcon to `var(--color-text-muted)`
		set style `display` of SummaryDot to `none`
	end
	else
	begin
		set style `background` of SummaryChip to `var(--color-chip-heat-bg)`
		set style `background-color` of SummaryChipIcon to `var(--color-chip-heat-fg)`
		set style `display` of SummaryDot to `block`
	end
	return
!! @hash b874b78c
!!!
!! Build today's date as "Mon 23 Apr" into TempStr. Uses DayNames / MonthNames lookup tables built once during synchronous startup.
FormatTodayString:
	put the day into DateD
	put the day number into DateDN
	put the month into DateM
	put element DateD of DayNames into DayName
	put element DateM of MonthNames into MonthName
	put DayName cat ` ` cat DateDN cat ` ` cat MonthName into TempStr
	return
!! @hash 6a52d8f9
!!!
!! Convert a temperature string "X.Y" into integer tenths (e.g. "20.5" → 205, "-1.7" → -17). Uses TempStr in, TempTenths out.
!!
!! Negative inputs need a sign-strip pass first because parsing `left 2 of '-0.5'` yields "-0" → 0, silently losing the sign for sub-1° magnitudes. We strip the leading `-`, parse the magnitude, then flip the sign back at the end.
ToTenths:
	put 0 into TempTenths
	if TempStr is empty return
	clear NegativeFlag
	if left 1 of TempStr is `-`
	begin
		set NegativeFlag
		put from 1 of TempStr into TempStr
	end
	put the index of `.` in TempStr into DotIdx
	if DotIdx is less than 0
	begin
		put the value of TempStr into TempTenths
		multiply TempTenths by 10
	end
	else
	begin
		put the value of left DotIdx of TempStr into TempTenths
		multiply TempTenths by 10
		increment DotIdx
		put the value of from DotIdx of TempStr into DecPart
		add DecPart to TempTenths
	end
	if NegativeFlag multiply TempTenths by -1
	return
!! @hash ead9f49b
!!!
!! Reverse of ToTenths: integer tenths → "X.Y" string. TempTenths in, TempStr out. Used after target steppers to convert the internal tenths value back to display form.
TenthsToString:
	put TempTenths into AvgInt
	put TempTenths modulo 10 into AvgDec
	divide AvgInt by 10
	put AvgInt cat `.` cat AvgDec into TempStr
	return
!! @hash 3855d409
!!!
!! Render the contents of one room row. Caller must set RoomIndex, IndexStr, and Room first; the per-row DOM has already been built by BuildHomeScreen's render-loop, so this is content-only updates (room name, heating tag, offline tag, subline, temperature, chip styling).
!!
!! The subline summarises the room's current schedule context:
!!
!! Sensor row → "Outdoor sensor".
!!
!! Offline row → the offlineReason text from BuildRoomEntry ("Thermometer not reporting", "Relay not responding", etc).
!!
!! On mode → "<target>°" (the held setpoint).
!!
!! Timed mode → "<nextTarget>°→<nextTime>" for an active period, or "Off until <nextTime>" with BG prefix for an inter-period gap; suffix " (A)" when Advance is active.
!!
!! Boost mode → "Boost · <minutes-left> · <target>°".
!!
!! Battery-low and warn-state messages are appended for online rooms.
!!
!! Setpoint slot is left empty pending a more useful per-room secondary value. Element stays attached so the layout slot is reserved.
RenderRoom:
	put property `mode` of Room into Mode
	put property `temp` of Room into TempVal
	put property `target` of Room into TargetTemp
	put property `offline` of Room into Offline
	put property `sensor` of Room into Sensor
	put property `boost` of Room into BoostVal
	put property `nextTime` of Room into NextTime
	put property `nextTarget` of Room into NextTarget
	put property `nextPrefix` of Room into NextPrefix
    put property `name` of Room into NameText
    put property `advance` of Room into Advance
	if Advance is empty put `-` into Advance

	clear CallingForHeat
	if property `calling` of Room is `yes` set CallingForHeat

	attach RoomName to `room-` cat IndexStr cat `-name`
	set the content of RoomName to NameText
	if CallingForHeat set style `color` of RoomName to `var(--color-accent)`
	else set style `color` of RoomName to `#2F75B5`

	attach HeatingTag to `room-` cat IndexStr cat `-heating-tag`
	if CallingForHeat set style `display` of HeatingTag to `inline-flex`
	else set style `display` of HeatingTag to `none`

	attach OfflineTag to `room-` cat IndexStr cat `-offline-tag`
	if Offline is `yes` set style `display` of OfflineTag to `inline-flex`
	else set style `display` of OfflineTag to `none`

	put empty into SublineText
	if Sensor is `yes` put `Outdoor sensor` into SublineText
	else if Offline is `yes` put property `offlineReason` of Room into SublineText
	else
	begin
		if Mode is `On`
		begin
			if TargetTemp is not empty put TargetTemp cat `°` into SublineText
		end
		else if Mode is `Timed`
		begin
			if NextTime is not empty
			begin
				if NextPrefix is `BG ` put `Off until ` cat NextTime into SublineText
				else put NextTarget cat `°→` cat NextTime into SublineText
				if Advance is `A` put SublineText cat ` (A)` into SublineText
			end
			else if NextTarget is not empty
			begin
				if NextPrefix is `BG ` put `Off` into SublineText
				else put NextTarget cat `°` into SublineText
			end
		end
		else if Mode is `Boost`
		begin
			if BoostVal is empty put `Boost` into SublineText
			else put `Boost · ` cat BoostVal cat ` left` into SublineText
			if TargetTemp is not empty put SublineText cat ` · ` cat TargetTemp cat `°` into SublineText
		end
	end

!	Battery-low + warn-state messages, appended for online rooms (offline
!	rooms already carry a more important status message).
	if Sensor is `no`
	begin
		if Offline is `no`
		begin
			if property `batteryLow` of Room is `yes`
			begin
				if SublineText is empty put `Battery low` into SublineText
				else put SublineText cat ` · Battery low` into SublineText
			end
			put property `warnMessage` of Room into WarnMessage
			if WarnMessage is not empty
			begin
				if SublineText is empty put WarnMessage into SublineText
				else put SublineText cat ` · ` cat WarnMessage into SublineText
			end
		end
	end

	attach Subline to `room-` cat IndexStr cat `-subline`
	set the content of Subline to SublineText

	attach TempEl to `room-` cat IndexStr cat `-temp`
	if TempVal is empty set the content of TempEl to `—`
	else set the content of TempEl to TempVal
	if Offline is `yes` set style `color` of TempEl to `var(--color-text-disabled)`
	else set style `color` of TempEl to `var(--color-text-primary)`

!	Setpoint slot left empty pending a more useful per-room secondary value.
!	Element kept attached so the layout slot is reserved.
	attach Setpoint to `room-` cat IndexStr cat `-setpoint`
	set the content of Setpoint to empty

	gosub to ApplyChipStyle
	return
!! @hash 41f9abfb
!!!
!! Decide the chip background / foreground / icon-url and apply them.
!!
!! Priority order: sensor (outdoor) → offline → boost-active → Off → On → calling-for-heat → default (Timed, not heating). Boost is detected via BoostVal (the "N mins left" string) rather than Mode so it can layer over Off or Timed even when the controller's mode hasn't yet rolled to `boost`.
!!
!! The icon is rendered as a CSS mask so the same SVG can be tinted via background-color — both `mask` and `-webkit-mask` are set for cross-browser support.
ApplyChipStyle:
	put `var(--color-chip-ok-bg)` into ChipBg
	put `var(--color-chip-ok-fg)` into ChipFg
	put `resources/icon/clock.svg` into ChipIconUrl

	if Sensor is `yes`
	begin
		put `var(--color-chip-neutral-bg)` into ChipBg
		put `var(--color-chip-neutral-fg)` into ChipFg
		put `resources/icon/sensor.svg` into ChipIconUrl
	end
	else if Offline is `yes`
	begin
		put `var(--color-chip-warn-bg)` into ChipBg
		put `var(--color-chip-warn-fg)` into ChipFg
		put `resources/icon/offline.svg` into ChipIconUrl
	end
	else if BoostVal is not empty
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
		put `resources/icon/boost.svg` into ChipIconUrl
	end
	else if Mode is `Off`
	begin
		put `var(--color-chip-neutral-bg)` into ChipBg
		put `var(--color-chip-neutral-fg)` into ChipFg
		put `resources/icon/off.svg` into ChipIconUrl
	end
	else if Mode is `On`
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
		put `resources/icon/on.svg` into ChipIconUrl
	end
	else if CallingForHeat
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
	end

	attach Chip to `room-` cat IndexStr cat `-chip`
	set style `background` of Chip to ChipBg

	attach ChipIcon to `room-` cat IndexStr cat `-chip-icon`
	set style `background-color` of ChipIcon to ChipFg
	put `url(` cat ChipIconUrl cat `) center/contain no-repeat` into MaskCss
	set style `mask` of ChipIcon to MaskCss
	set style `-webkit-mask` of ChipIcon to MaskCss
	return
!! @hash 2ba0f914
!!!
!! Terminal failure handler. Reached via `or go to LoadFailed` from every `rest get` template fetch in the bootstrap region — a missing or malformed Webson template means the UI can't render, so we alert and stop rather than limping on with broken state.
LoadFailed:
	alert `Failed to load UI template`
	stop
!! @hash 34c0ed2e
!!!
