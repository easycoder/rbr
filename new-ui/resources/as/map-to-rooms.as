!! Map-to-rooms translation module. Receives the controller's legacy map JSON from shell.as and translates it into the new-UI shape (Title-case modes, "X.Y" temperature strings, schedule projection, offline classification, etc).
!!
!! Loaded once by shell.as via `run ... as MapToRoomsModule`. On every controller map push, shell.as sends the Map dict here and gets back a Result dict with all the translated state. The module is otherwise stateless — each Translate call is a self-contained transformation.
!!
!! Reply payload (keys on Result):
!!   `rooms`               — filtered new-UI RoomsList (outdoor sensor stripped)
!!   `roomCount`           — count of entries in `rooms`
!!   `outsideTemp`         — outdoor temperature as "X.Y" string, or empty
!!   `outsideSensor`       — outdoor sensor name, or empty
!!   `frostTrigger`        — frost-protection trigger, or empty
!!   `outsideRoomFound`    — `yes` / `no` (outdoor-sensor slot was present)
!!   `outsideRoomLegacyIdx`— legacy index of the outdoor slot (for the Devices editor)
!!   `profiles`            — full profiles array (passed through for sheet editors)
!!   `currentProfile`      — active profile index (calendar-resolved)
!!   `activeProfile`       — the active profile dict
!!   `activeProfileName`   — its name
!!   `systemName`          — Map.name
!!   `systemType`          — Map.systemType (defaulted to "Boiler" when missing)
!!   `requestRelay`        — Map.request (the demand-relay name)
!!   `calendarOn`          — `on` / `off`

	script MapToRooms

	variable Map
	variable Result

	variable Profiles
	variable CurrentProfile
	variable ActiveProfile
	variable ActiveProfileName
	variable SystemName
	variable SystemType
	variable RequestRelay
	variable CalendarOn
	variable CalendarData
	variable CalendarEntry
	variable DayN
	variable DayProfileName
	variable LoopJ
	variable ProfileN
	variable LegacyProfileCount

	variable RoomsList
	variable RoomsListIdx
	variable RoomCount
	variable OutsideTemp
	variable OutsideSensor
	variable FrostTrigger
	variable OutsideRoomFound
	variable OutsideRoomLegacyIdx

	variable LegacyRooms
	variable LegacyRoomCount
	variable LegacyIdx
	variable LegacyRoom
	variable LegacyRelays
	variable LegacyRelayCount

	variable NewRoom
	variable LegacyName
	variable LegacyMode
	variable LegacyPrevMode
	variable PrevMode
	variable Mode
	variable Advance
	variable LegacyTemp
	variable LegacyTarget
	variable LegacyStatus
	variable LegacyStatusMessage
	variable LegacyRelaysFailed
	variable LegacyRelaysTotal
	variable LegacyRelayMsg
	variable LegacyLinked
	variable OfflineReason
	variable LegacyBattery
	variable BoostUntil
	variable BoostRemaining
	variable BoostText

	variable LegacyPeriods
	variable LegacyPeriodsCount
	variable LegacyPeriod
	variable LoopK
	variable NowMinutes
	variable OnMinutes
	variable OffMinutes
	variable InThisPeriod
	variable PeriodFound
	variable NextOnMinutes
	variable NextOnStr
	variable BgTemp
	variable BgTempStr
	variable AfterMinutes
	variable DisplayPeriodIdx
	variable NextTimeStr
	variable NextTempVal
	variable NextTempStr

!	One-off override + morning-start projection.
	variable MapOverrides
	variable MapOverride
	variable PeriodOnMin
	variable MorningOnMinutes
	variable MorningPeriodCount

	variable TempStr
	variable TempTenths
	variable Hundredths
	variable TempInt
	variable DotIdx
	variable DecPart

	on message go to Translate
	release parent
	stop
!! @hash d70757d5
!!!
!! Message handler. Unpacks the Map from the message, runs the translation, packs the output dict, ships it back. Boolean flags (CalendarOn, OutsideRoomFound) travel as "on"/"off" / "yes"/"no" strings because boolean state doesn't round-trip cleanly through JSON.
Translate:
	put the message into Map
	gosub to TranslateMap

	put `{}` into Result
	set property `rooms` of Result to RoomsList
	set property `roomCount` of Result to RoomCount
	set property `outsideTemp` of Result to OutsideTemp
	set property `outsideSensor` of Result to OutsideSensor
	set property `frostTrigger` of Result to FrostTrigger
	if OutsideRoomFound set property `outsideRoomFound` of Result to `yes`
	else set property `outsideRoomFound` of Result to `no`
	set property `outsideRoomLegacyIdx` of Result to OutsideRoomLegacyIdx
	set property `profiles` of Result to Profiles
	set property `currentProfile` of Result to CurrentProfile
	set property `activeProfile` of Result to ActiveProfile
	set property `activeProfileName` of Result to ActiveProfileName
	set property `systemName` of Result to SystemName
	set property `systemType` of Result to SystemType
	set property `requestRelay` of Result to RequestRelay
	if CalendarOn set property `calendarOn` of Result to `on`
	else set property `calendarOn` of Result to `off`

	send Result to sender
	stop
!! @hash 2571dbc6
!!!
!! Walk the controller's map, build the new-UI RoomsList from scratch. Resolves the active profile via the calendar (when on) or Map.profile (when off), captures system-wide fields, and filters out the outdoor sensor entry into separate OutsideTemp / OutsideSensor / FrostTrigger state.
!!
!! The outdoor sensor entry is the "room with empty relays" slot — pinned by legacy index for the Devices editor to write back to, with its temperature feeding OutsideTemp.
TranslateMap:
	put property `profiles` of Map into Profiles
	put property `profile` of Map into CurrentProfile
	if CurrentProfile is empty put 0 into CurrentProfile

!	Calendar lock state — when on, manual profile selection is masked in the UI.
	clear CalendarOn
	if property `calendar` of Map is `on` set CalendarOn

!	If the calendar is on, today's profile-name overrides Map.profile.
!	`the day` returns 0=Sunday (JS getDay), so shift +6 mod 7 to make
!	Monday=0 to match the Monday-first calendar-data array.
	if property `calendar` of Map is `on`
	begin
		put property `calendar-data` of Map into CalendarData
		if CalendarData is not empty
		begin
			put the day into DayN
			add 6 to DayN
			put DayN modulo 7 into DayN
			put element DayN of CalendarData into CalendarEntry
			if CalendarEntry is not empty
			begin
				put property `day` cat DayN cat `-profile` of CalendarEntry into DayProfileName
				if DayProfileName is not empty
				begin
					put the json count of Profiles into LegacyProfileCount
					put 0 into LoopJ
					while LoopJ is less than LegacyProfileCount
					begin
						put element LoopJ of Profiles into ProfileN
						if property `name` of ProfileN is DayProfileName put LoopJ into CurrentProfile
						increment LoopJ
					end
				end
			end
		end
	end

	put element CurrentProfile of Profiles into ActiveProfile
	put property `name` of ActiveProfile into ActiveProfileName
	put property `name` of Map into SystemName
	put property `systemType` of Map into SystemType
	if SystemType is empty put `Boiler` into SystemType
	put property `request` of Map into RequestRelay
	put property `rooms` of ActiveProfile into LegacyRooms
	put the json count of LegacyRooms into LegacyRoomCount

	put `[]` into RoomsList
	put 0 into RoomsListIdx
	put empty into OutsideTemp
	put empty into OutsideSensor
	put empty into FrostTrigger
	clear OutsideRoomFound
	put 0 into OutsideRoomLegacyIdx

	put 0 into LegacyIdx
	while LegacyIdx is less than LegacyRoomCount
	begin
		put element LegacyIdx of LegacyRooms into LegacyRoom
		put property `relays` of LegacyRoom into LegacyRelays
		put the json count of LegacyRelays into LegacyRelayCount
		if LegacyRelayCount is 0
		begin
!			Outdoor sensor entry: pin its slot index for the device editor,
!			capture its sensor name + frost trigger, take its temperature.
!			Skip the room (no card).
			set OutsideRoomFound
			put LegacyIdx into OutsideRoomLegacyIdx
			put property `sensor` of LegacyRoom into OutsideSensor
			put property `ptemp` of LegacyRoom into FrostTrigger
			put property `temperature` of LegacyRoom into LegacyTemp
			if LegacyTemp is not empty
			begin
				if LegacyTemp is not 0
				begin
					put LegacyTemp into TempStr
					gosub to FormatHundredths
					put TempStr into OutsideTemp
				end
			end
		end
		else
		begin
			gosub to BuildRoomEntry
			set element RoomsListIdx of RoomsList to NewRoom
			increment RoomsListIdx
		end
		increment LegacyIdx
	end
	put RoomsListIdx into RoomCount
	return
!! @hash 245f82f6
!!!
!! Translate one legacy controller-map room into a new-UI room entry. Inputs: LegacyRoom (the controller-format slot), RoomsListIdx (the position in the filtered RoomsList). Output: NewRoom, a fresh JSON object stored back into RoomsList by the caller.
!!
!! Mode translation: lowercase → Title-case (`timed` → `Timed`, `on` → `On`, `boost` → `Boost`, anything else → `Off`). Boost is a peer mode in the new UI; when the controller reports `boost`, we surface that as Mode="Boost" and capture `prevmode` (Title-case) on NewRoom.prevMode so SyncCurrentRoomToMap can round-trip it back.
!!
!! Advance: `A` (active) / `-` (normal). Empty/missing defaults to `-`.
!!
!! Temperature: legacy hundredths → "X.Y" string via FormatHundredths. Zero or empty becomes empty so the UI shows the em-dash placeholder.
!!
!! Target: always populated, defaulting to "20.0" when the legacy field is missing or 0. Off rooms keep a target so the user can adjust it before applying a Boost.
!!
!! Offline classification. A relay that's not responding is a real fault — mark offline with "Relay not responding". A linked room whose sensor has never reported is the one sensor case that goes offline (no last-known value to show). A stale sensor on an established room is NOT offline by itself: the controller preserves the last known temperature, and we keep showing it with a soft "No recent change" warn message rather than blanking the display.
!!
!! Warn-state message: surface the controller's diagnostic for online rooms. A sensor-staleness message ("Sensor: no report for N min") is softened to "No recent change"; other warn messages (e.g. relay failures shy of the offline threshold) pass through verbatim. The same softening applies to a `fail` status when the cause is sensor-side.
!!
!! Battery: flag low (≤20%) — 0/empty means "no reading" and isn't flagged. The raw value is also stored for the Info sheet.
!!
!! Boost remaining: when mode is `boost`, compute remaining time from the `until` ms timestamp the controller stores when the boost was applied. Round up to the next minute, format as "N min(s)". The minute-by-minute countdown between map pushes is handled separately by the parent's BoostTick.
!!
!! Schedule projection — what's the controller heating to right now and when does it next change? Sets `nextTarget`, `nextTime`, and `nextPrefix` on NewRoom so the subline can flag background-temp gaps with "BG " prefix and an "Off until <next on>" form.
!!
!! Advance override: when Advance is `A`, project the schedule one slot forward. From a current period — Advance ends it early and the room joins the inter-period gap (displayed as "Off until <next on>" with BG prefix). From background — Advance jumps the next period forward (display that period's temp and off time, no BG prefix).
!!
!! `calling` (relay state for chip styling) is taken straight from the controller's `relay` field, not re-derived. The controller already accounts for unlinked relays, boost overlay, and hysteresis-free temp-vs-target comparison; re-deriving in the UI's threshold ends up wrong.
BuildRoomEntry:
	put `{}` into NewRoom
	put property `name` of LegacyRoom into LegacyName
	set property `name` of NewRoom to LegacyName
	set property `id` of NewRoom to `room-` cat RoomsListIdx
	set property `legacyIdx` of NewRoom to LegacyIdx
	set property `sensor` of NewRoom to `no`

	put property `mode` of LegacyRoom into LegacyMode
	put `Off` into Mode
	put empty into PrevMode
	if LegacyMode is `timed` put `Timed` into Mode
	else if LegacyMode is `on` put `On` into Mode
	else if LegacyMode is `boost`
	begin
		put `Boost` into Mode
		put property `prevmode` of LegacyRoom into LegacyPrevMode
		put `Off` into PrevMode
		if LegacyPrevMode is `timed` put `Timed` into PrevMode
		else if LegacyPrevMode is `on` put `On` into PrevMode
	end
    set property `mode` of NewRoom to Mode
    set property `prevMode` of NewRoom to PrevMode

    put property `advance` of LegacyRoom into Advance
	if Advance is empty put `-` into Advance
	set property `advance` of NewRoom to Advance

	put property `temperature` of LegacyRoom into LegacyTemp
	if LegacyTemp is empty set property `temp` of NewRoom to empty
	else if LegacyTemp is 0 set property `temp` of NewRoom to empty
	else
	begin
		put LegacyTemp into TempStr
		gosub to FormatHundredths
		set property `temp` of NewRoom to TempStr
	end

	put property `target` of LegacyRoom into LegacyTarget
	if LegacyTarget is empty set property `target` of NewRoom to `20.0`
	else if LegacyTarget is 0 set property `target` of NewRoom to `20.0`
	else
	begin
		put `` cat LegacyTarget into TempStr
		put the index of `.` in TempStr into DotIdx
		if DotIdx is less than 0 put TempStr cat `.0` into TempStr
		set property `target` of NewRoom to TempStr
	end

	set property `offline` of NewRoom to `no`
	set property `partial` of NewRoom to `no`
	put `No signal` into OfflineReason
	put property `status` of LegacyRoom into LegacyStatus
	put property `statusMessage` of LegacyRoom into LegacyStatusMessage
	put property `linked` of LegacyRoom into LegacyLinked

	if LegacyLinked is `yes`
	begin
		put property `temperature` of LegacyRoom into LegacyTemp
		if LegacyTemp is empty
		begin
			set property `offline` of NewRoom to `yes`
			put `Thermometer not reporting` into OfflineReason
		end
	end

	if LegacyStatus is `fail`
	begin
		if the index of `Relay` in LegacyStatusMessage is greater than -1
		begin
			set property `offline` of NewRoom to `yes`
			put `Relay not responding` into OfflineReason
		end
	end

	set property `offlineReason` of NewRoom to OfflineReason

!	Relay health comes straight from the controller's per-relay counts, so a
!	dead relay among several is visible even when the room status says
!	something else (a stale sensor pushes the status to `warn`). partial =
!	some, but not all, relays faulty — the room still heats from the rest.
	put property `relaysFailed` of LegacyRoom into LegacyRelaysFailed
	put property `relaysTotal` of LegacyRoom into LegacyRelaysTotal
	if LegacyStatus is `partial` set property `partial` of NewRoom to `yes`
	else if LegacyRelaysFailed is not empty
	begin
		if LegacyRelaysFailed is greater than 0
			if LegacyRelaysTotal is not empty
				if LegacyRelaysFailed is less than LegacyRelaysTotal set property `partial` of NewRoom to `yes`
	end

	set property `warnMessage` of NewRoom to empty
	if property `offline` of NewRoom is `no`
	begin
		if property `partial` of NewRoom is `yes`
		begin
!			Name the relay that is not answering, in the controller's words.
			put property `relayMessage` of LegacyRoom into LegacyRelayMsg
			if LegacyRelayMsg is not empty set property `warnMessage` of NewRoom to LegacyRelayMsg
			else if LegacyStatusMessage is not empty set property `warnMessage` of NewRoom to LegacyStatusMessage
		end
		else if LegacyStatus is `warn`
		begin
			if the index of `Relay` in LegacyStatusMessage is greater than -1
				set property `warnMessage` of NewRoom to LegacyStatusMessage
			else if the index of `Sensor` in LegacyStatusMessage is greater than -1
				set property `warnMessage` of NewRoom to `No recent change`
			else if LegacyStatusMessage is not empty
				set property `warnMessage` of NewRoom to LegacyStatusMessage
		end
		else if LegacyStatus is `fail`
		begin
			if the index of `Sensor` in LegacyStatusMessage is greater than -1
				set property `warnMessage` of NewRoom to `No recent change`
		end
	end

	set property `batteryLow` of NewRoom to `no`
	put property `battery` of LegacyRoom into LegacyBattery
	set property `battery` of NewRoom to LegacyBattery
	if LegacyBattery is not empty
	begin
		if LegacyBattery is greater than 0
		begin
			if LegacyBattery is less than 21 set property `batteryLow` of NewRoom to `yes`
		end
	end

	set property `relay` of NewRoom to property `relay` of LegacyRoom
	set property `humidity` of NewRoom to property `humidity` of LegacyRoom
	set property `sensorAge` of NewRoom to property `sensorAge` of LegacyRoom

	set property `boost` of NewRoom to empty
	set property `boostRemaining` of NewRoom to 0
	set property `boostUntilMs` of NewRoom to 0
	if LegacyMode is `boost`
	begin
		put property `until` of LegacyRoom into BoostUntil
		if BoostUntil is not empty
		begin
			set property `boostUntilMs` of NewRoom to BoostUntil
			put BoostUntil into BoostRemaining
			take the timestamp from BoostRemaining
			if BoostRemaining is greater than 0
			begin
				divide BoostRemaining by 60000
				add 1 to BoostRemaining
				if BoostRemaining is 1 put `1 min` into BoostText
				else put BoostRemaining cat ` mins` into BoostText
				set property `boost` of NewRoom to BoostText
				set property `boostRemaining` of NewRoom to BoostRemaining
			end
		end
	end

	set property `nextTime` of NewRoom to empty
	set property `nextTarget` of NewRoom to empty
	set property `nextPrefix` of NewRoom to empty

	put the hour into NowMinutes
	multiply NowMinutes by 60
	add the minute to NowMinutes

	put property `periods` of LegacyRoom into LegacyPeriods
	clear PeriodFound
	if LegacyPeriods is not empty
	begin
		put the json count of LegacyPeriods into LegacyPeriodsCount
		put 0 into LoopK
		while LoopK is less than LegacyPeriodsCount
		begin
			put element LoopK of LegacyPeriods into LegacyPeriod
			put property `on` of LegacyPeriod into TempStr
			gosub to ParseTimeMinutes
			put TempTenths into OnMinutes
			put property `off` of LegacyPeriod into TempStr
			gosub to ParseTimeMinutes
			put TempTenths into OffMinutes
			clear InThisPeriod
			if OnMinutes is OffMinutes set InThisPeriod
			else if OnMinutes is less than OffMinutes
			begin
				if NowMinutes is not less than OnMinutes
					if NowMinutes is less than OffMinutes
						set InThisPeriod
			end
			else
			begin
				! wraps midnight
				if NowMinutes is not less than OnMinutes set InThisPeriod
				else if NowMinutes is less than OffMinutes set InThisPeriod
			end
			if InThisPeriod
			begin
				put property `off` of LegacyPeriod into NextTimeStr
				put property `temp` of LegacyPeriod into NextTempVal
				set property `nextTime` of NewRoom to NextTimeStr
				put `` cat NextTempVal into NextTempStr
				put the index of `.` in NextTempStr into DotIdx
				if DotIdx is less than 0 put NextTempStr cat `.0` into NextTempStr
				set property `nextTarget` of NewRoom to NextTempStr
				set PeriodFound
				put LegacyPeriodsCount into LoopK
			end
			increment LoopK
		end
	end

	if not PeriodFound
	begin
		put property `background-temp` of Map into BgTemp
		if BgTemp is empty put 12 into BgTemp
		put `` cat BgTemp into BgTempStr
		put the index of `.` in BgTempStr into DotIdx
		if DotIdx is less than 0 put BgTempStr cat `.0` into BgTempStr
		set property `nextTarget` of NewRoom to BgTempStr
		set property `nextPrefix` of NewRoom to `BG `

		if LegacyPeriods is not empty
		begin
			put 1500 into NextOnMinutes
			put empty into NextOnStr
			put 0 into LoopK
			while LoopK is less than LegacyPeriodsCount
			begin
				put element LoopK of LegacyPeriods into LegacyPeriod
				put property `on` of LegacyPeriod into TempStr
				gosub to ParseTimeMinutes
				if TempTenths is greater than NowMinutes
					if TempTenths is less than NextOnMinutes
					begin
						put TempTenths into NextOnMinutes
						put property `on` of LegacyPeriod into NextOnStr
					end
				increment LoopK
			end
			if NextOnStr is empty
			begin
				put 1500 into NextOnMinutes
				put 0 into LoopK
				while LoopK is less than LegacyPeriodsCount
				begin
					put element LoopK of LegacyPeriods into LegacyPeriod
					put property `on` of LegacyPeriod into TempStr
					gosub to ParseTimeMinutes
					if TempTenths is less than NextOnMinutes
					begin
						put TempTenths into NextOnMinutes
						put property `on` of LegacyPeriod into NextOnStr
					end
					increment LoopK
				end
			end
			set property `nextTime` of NewRoom to NextOnStr
		end
	end

	if Advance is `A`
	begin
		if LegacyPeriods is not empty
		begin
			if PeriodFound
			begin
				put NextTimeStr into TempStr
				gosub to ParseTimeMinutes
				put TempTenths into AfterMinutes
			end
			else put NowMinutes into AfterMinutes

			put 1500 into NextOnMinutes
			put -1 into DisplayPeriodIdx
			put 0 into LoopK
			while LoopK is less than LegacyPeriodsCount
			begin
				put element LoopK of LegacyPeriods into LegacyPeriod
				put property `on` of LegacyPeriod into TempStr
				gosub to ParseTimeMinutes
				if TempTenths is greater than AfterMinutes
					if TempTenths is less than NextOnMinutes
					begin
						put TempTenths into NextOnMinutes
						put LoopK into DisplayPeriodIdx
					end
				increment LoopK
			end
			if DisplayPeriodIdx is less than 0
			begin
				put 1500 into NextOnMinutes
				put 0 into LoopK
				while LoopK is less than LegacyPeriodsCount
				begin
					put element LoopK of LegacyPeriods into LegacyPeriod
					put property `on` of LegacyPeriod into TempStr
					gosub to ParseTimeMinutes
					if TempTenths is less than NextOnMinutes
					begin
						put TempTenths into NextOnMinutes
						put LoopK into DisplayPeriodIdx
					end
					increment LoopK
				end
			end
			if DisplayPeriodIdx is not less than 0
			begin
				put element DisplayPeriodIdx of LegacyPeriods into LegacyPeriod
				if PeriodFound
				begin
					put property `on` of LegacyPeriod into NextTimeStr
					set property `nextTime` of NewRoom to NextTimeStr
					put property `background-temp` of Map into BgTemp
					if BgTemp is empty put 12 into BgTemp
					put `` cat BgTemp into BgTempStr
					put the index of `.` in BgTempStr into DotIdx
					if DotIdx is less than 0 put BgTempStr cat `.0` into BgTempStr
					set property `nextTarget` of NewRoom to BgTempStr
					set property `nextPrefix` of NewRoom to `BG `
				end
				else
				begin
					put property `off` of LegacyPeriod into NextTimeStr
					put property `temp` of LegacyPeriod into NextTempVal
					set property `nextTime` of NewRoom to NextTimeStr
					put `` cat NextTempVal into NextTempStr
					put the index of `.` in NextTempStr into DotIdx
					if DotIdx is less than 0 put NextTempStr cat `.0` into NextTempStr
					set property `nextTarget` of NewRoom to NextTempStr
					set property `nextPrefix` of NewRoom to empty
				end
			end
		end
	end

!	One-off override plus the scheduled morning start. The override lives at the top
!	level of the controller map, keyed by room name, so it applies whichever profile
!	the calendar picks for the day; it is surfaced raw (kind / time / date) and the
!	shell formats it, keeping one place responsible for the wording. The morning
!	start is the earliest `on` among the room's periods — the same period the
!	controller treats as the one-day override's target — and is used only to
!	pre-fill the time popup on a first use.
	set property `overrideKind` of NewRoom to empty
	set property `overrideTime` of NewRoom to empty
	set property `overrideDate` of NewRoom to empty
	set property `morningOn` of NewRoom to empty

	put property `overrides` of Map into MapOverrides
	if MapOverrides is not empty
	begin
		put property LegacyName of MapOverrides into MapOverride
		if MapOverride is not empty
		begin
			set property `overrideKind` of NewRoom to property `kind` of MapOverride
			if property `kind` of MapOverride is `start` set property `overrideTime` of NewRoom to property `on` of MapOverride
			set property `overrideDate` of NewRoom to property `date` of MapOverride
		end
	end

	put 1500 into MorningOnMinutes
	put 0 into MorningPeriodCount
	if LegacyPeriods is not empty put the json count of LegacyPeriods into MorningPeriodCount
	put 0 into LoopK
	while LoopK is less than MorningPeriodCount
	begin
		put element LoopK of LegacyPeriods into LegacyPeriod
		put property `on` of LegacyPeriod into TempStr
		gosub to ParseTimeMinutes
		put TempTenths into PeriodOnMin
		put property `off` of LegacyPeriod into TempStr
		gosub to ParseTimeMinutes
		! Skip zero-length and wrap-around periods (on at or after off): neither
		! is the morning warm-up the Special action can shift.
		if PeriodOnMin is less than TempTenths
		begin
			if PeriodOnMin is less than MorningOnMinutes
			begin
				put PeriodOnMin into MorningOnMinutes
				set property `morningOn` of NewRoom to property `on` of LegacyPeriod
			end
		end
		increment LoopK
	end

	set property `calling` of NewRoom to `no`
	if property `relay` of LegacyRoom is `on` set property `calling` of NewRoom to `yes`
	return
!! @hash 4582c5e2
!!!
!! Convert TempStr (legacy hundredths integer, e.g. 1980) to "X.Y" string (19.8). In-place via TempStr — caller passes the integer in, gets the string back out.
FormatHundredths:
	put TempStr modulo 100 into Hundredths
	put TempStr into TempInt
	divide TempInt by 100
	divide Hundredths by 10
	put `` cat TempInt cat `.` cat Hundredths into TempStr
	return
!! @hash 0377473d
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
