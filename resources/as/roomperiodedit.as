!	Period Editor (new model: ON/OFF/temp triples)
!	Edits the room's `periods` array. Each period is {on, off, temp}.
!	Outside any period the controller targets the system `background-temp`.
!	Periods may wrap midnight (on > off).

	script RoomPeriodEditor

	import div MainPanel
		and variable Map
		and variable CurrentProfile
		and variable ClickIndex
		and variable Result

	div RoomName
	div DialogPanel
	div DialogTitle
	div DialogText
	div EditTimes
	div PeriodContent
	div PeriodInfo
	div OnHourField
	div OnMinuteField
	div OffHourField
	div OffMinuteField
	div TempField
	button DialogButton1
	button DialogButton2
	button TimesAddButton
	button TimesSaveButton
	button TimesCancelButton
	button TimesHelpButton
	button PeriodSave
	button PeriodDelete
	img OnHourUpButton
	img OnHourDownButton
	img OnMinuteUpButton
	img OnMinuteDownButton
	img OffHourUpButton
	img OffHourDownButton
	img OffMinuteUpButton
	img OffMinuteDownButton
	img TempUpButton
	img TempDownButton
	variable Webson
	variable Rooms
	variable RoomSpec
	variable Profiles
	variable Profile
	variable PeriodWebson
	variable PeriodInfoWebson
	variable PeriodEditorWebson
	variable Periods
	variable Period
	variable Period2
	variable NPeriods
	variable ThisPeriod
	variable OnHourValue
	variable OnMinuteValue
	variable OffHourValue
	variable OffMinuteValue
	variable OnTimeStr
	variable OffTimeStr
	variable TempValue
	variable Temp
	variable Value
	variable Editing
	variable Unsorted
	variable Changed
	variable RequestData
	variable HV
	variable MV
	variable P
	variable Q
	variable T
	variable T1
	variable T2

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	The schedule editor
	gosub to GetCurrentRooms
	put element ClickIndex of Rooms into RoomSpec

	clear MainPanel
	rest get Webson from `resources/webson/timeseditor.json?v=` cat now
	render Webson in MainPanel
	attach RoomName to `title-room-name`
	attach EditTimes to `edit-times`
	set the content of RoomName to property `name` of RoomSpec
	clear EditTimes
	rest get PeriodWebson from `resources/webson/period.json?v=` cat now
	rest get PeriodInfoWebson from `resources/webson/periodinfo.json?v=` cat now
	rest get PeriodEditorWebson from `resources/webson/roomperiodeditor.json?v=` cat now

	if RoomSpec has property `periods` put property `periods` of RoomSpec into Periods
	else put `[]` into Periods
	clear Changed
	clear Editing

	attach TimesAddButton to `edit-add-button`
	attach TimesSaveButton to `edit-save-button`
	attach TimesCancelButton to `edit-cancel-button`
	attach TimesHelpButton to `edit-help-button`

	put 0 into ThisPeriod
	gosub to RenderPeriods

	on click TimesAddButton
	begin
		if Editing stop
		put `{}` into Period
		set property `on` of Period to `06:00`
		set property `off` of Period to `08:00`
		set property `temp` of Period to `21.0`
		append Period to Periods
		set Changed
		gosub to SortPeriods
		gosub to RenderPeriods
	end

	on click TimesSaveButton
	begin
		if Editing gosub to CancelEditing
		gosub to SortPeriods
		set property `periods` of RoomSpec to Periods
		set element ClickIndex of Rooms to RoomSpec
		gosub to CopyRoomsToMap
		clear MainPanel
		go to Exit
	end

	on click TimesCancelButton
	begin
		clear MainPanel
		clear Changed
		go to Exit
	end

	on click TimesHelpButton
	begin
		clear MainPanel
		put `Help home RoomPeriodEdit` into Result
		exit
	end

	put `{}` into RequestData
	set property `action` of RequestData to empty
	set property `roomnumber` of RequestData to ClickIndex

	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	When an info panel is tapped it is replaced by an editor.
OnClickPeriodInfo:
	if Editing stop
	put the index of PeriodInfo into ThisPeriod
	go to ShowEditor

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Show a period editor. There's only a single instance.
ShowEditor:
	set Editing
	index PeriodContent to ThisPeriod
	clear PeriodContent
	put PeriodEditorWebson into Webson
	replace `/INDEX/` with ThisPeriod in Webson
	render Webson in PeriodContent
	attach OnHourUpButton to `on-hour-up`
	attach OnHourDownButton to `on-hour-down`
	attach OnMinuteUpButton to `on-minute-up`
	attach OnMinuteDownButton to `on-minute-down`
	attach OffHourUpButton to `off-hour-up`
	attach OffHourDownButton to `off-hour-down`
	attach OffMinuteUpButton to `off-minute-up`
	attach OffMinuteDownButton to `off-minute-down`
	attach TempUpButton to `temp-up`
	attach TempDownButton to `temp-down`
	attach OnHourField to `on-hour-text`
	attach OnMinuteField to `on-minute-text`
	attach OffHourField to `off-hour-text`
	attach OffMinuteField to `off-minute-text`
	attach TempField to `temp-text`
	attach PeriodSave to `period-save`
	attach PeriodDelete to `period-delete`

	put element ThisPeriod of Periods into Period
	put property `on` of Period into OnTimeStr
	put property `off` of Period into OffTimeStr
	put the value of left 2 of OnTimeStr into OnHourValue
	put the value of right 2 of OnTimeStr into OnMinuteValue
	put the value of left 2 of OffTimeStr into OffHourValue
	put the value of right 2 of OffTimeStr into OffMinuteValue
	put `` cat property `temp` of Period into Value
	if the position of `.` in Value is -1 multiply the value of Value by 10 giving TempValue
	else
	begin
		split Value on `.` giving Temp
		index Temp to 0
		multiply the value of Temp by 10 giving TempValue
		index Temp to 1
		add the value of Temp to TempValue
	end
	gosub to ShowValues

	on click OnHourUpButton
	begin
		if OnHourValue is 23 put -1 into OnHourValue
		add 1 to OnHourValue
		gosub to ShowValues
	end
	on click OnHourDownButton
	begin
		if OnHourValue is 0 put 24 into OnHourValue
		take 1 from OnHourValue
		gosub to ShowValues
	end
	on click OnMinuteUpButton
	begin
		if OnMinuteValue is 55 put -5 into OnMinuteValue
		add 5 to OnMinuteValue
		gosub to ShowValues
	end
	on click OnMinuteDownButton
	begin
		if OnMinuteValue is 0 put 60 into OnMinuteValue
		take 5 from OnMinuteValue
		gosub to ShowValues
	end
	on click OffHourUpButton
	begin
		if OffHourValue is 23 put -1 into OffHourValue
		add 1 to OffHourValue
		gosub to ShowValues
	end
	on click OffHourDownButton
	begin
		if OffHourValue is 0 put 24 into OffHourValue
		take 1 from OffHourValue
		gosub to ShowValues
	end
	on click OffMinuteUpButton
	begin
		if OffMinuteValue is 55 put -5 into OffMinuteValue
		add 5 to OffMinuteValue
		gosub to ShowValues
	end
	on click OffMinuteDownButton
	begin
		if OffMinuteValue is 0 put 60 into OffMinuteValue
		take 5 from OffMinuteValue
		gosub to ShowValues
	end
	on click TempUpButton
	begin
		add 5 to TempValue
		gosub to ShowValues
	end
	on click TempDownButton
	begin
		if TempValue is 0 stop
		take 5 from TempValue
		gosub to ShowValues
	end

	on click PeriodSave gosub to CancelEditing

	on click PeriodDelete
	begin
		attach DialogPanel to `dialog-panel`
		rest get Webson from `resources/webson/dialog-confirm.json?v=` cat now
		render Webson in DialogPanel
		attach DialogTitle to `dialog-title`
		attach DialogText to `dialog-text`
		attach DialogButton1 to `dialog-button1`
		attach DialogButton2 to `dialog-button2`
		set the content of DialogTitle to `Confirm deletion`
		set the content of DialogText to `Are you sure you want to remove this period?`
		set the content of DialogButton1 to `Yes`
		set the content of DialogButton2 to `No`
		on click DialogButton1
		begin
			clear DialogPanel
			json delete element ThisPeriod of Periods
			set Changed
			gosub to RenderPeriods
			clear Editing
		end
		on click DialogButton2 clear DialogPanel
	end
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Cancel editing and sort the periods
CancelEditing:
	set Changed
	clear Editing
	gosub to ShowValues
	gosub to SortPeriods
	gosub to RenderPeriods
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Show the current values for this period and write them back into Period.
ShowValues:
	put `0` cat OnHourValue into Value
	set the content of OnHourField to right 2 of Value
	put right 2 of Value into OnTimeStr
	put `0` cat OnMinuteValue into Value
	set the content of OnMinuteField to right 2 of Value
	put OnTimeStr cat `:` cat right 2 of Value into OnTimeStr

	put `0` cat OffHourValue into Value
	set the content of OffHourField to right 2 of Value
	put right 2 of Value into OffTimeStr
	put `0` cat OffMinuteValue into Value
	set the content of OffMinuteField to right 2 of Value
	put OffTimeStr cat `:` cat right 2 of Value into OffTimeStr

	divide TempValue by 10 giving Temp
	put Temp cat `.` cat TempValue modulo 10 into Temp
	put Temp cat `&deg;C` into Value
	set the content of TempField to Value

	put element ThisPeriod of Periods into Period
	set property `on` of Period to OnTimeStr
	set property `off` of Period to OffTimeStr
	set property `temp` of Period to Temp
	set element ThisPeriod of Periods to Period
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Sort the periods by ON time (ascending). Wrap-around periods (on > off)
!	keep their position in the natural ordering of on times.
SortPeriods:
	put the json count of Periods into NPeriods
	if NPeriods is less than 2 return
	push P
	push Q
	set Unsorted
	while Unsorted
	begin
		clear Unsorted
		put 1 into P
		while P is less than NPeriods
		begin
			take 1 from P giving Q
			put element Q of Periods into Period
			put property `on` of Period into T
			gosub to ParseTime
			put T into T1
			put element P of Periods into Period
			put property `on` of Period into T
			gosub to ParseTime
			put T into T2
			if T2 is less than T1
			begin
				put Period into Period2
				set element P of Periods to element Q of Periods
				set element Q of Periods to Period2
				set Unsorted
				set Changed
			end
			add 1 to P
		end
	end
	pop Q
	pop P
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Render all the periods.
RenderPeriods:
	push P
	put the json count of Periods into NPeriods
	set the elements of PeriodContent to NPeriods
	set the elements of PeriodInfo to NPeriods
	clear EditTimes
	put 0 into P
	while P is less than NPeriods
	begin
		index PeriodContent to P
		index PeriodInfo to P
		put PeriodWebson into Webson
		replace `/INDEX/` with P in Webson
		render Webson in EditTimes
		attach PeriodContent to `period-content-` cat P
		add 1 to P
	end
	put 0 into P
	while P is less than NPeriods
	begin
		gosub to RenderPeriod
		add 1 to P
	end
	pop P
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Render a single period info row.
RenderPeriod:
	put PeriodInfoWebson into Webson
	replace `/INDEX/` with P in Webson
	index PeriodInfo to P
	index PeriodContent to P
	clear PeriodContent
	render Webson in PeriodContent

	put element P of Periods into Period
	put property `on` of Period into OnTimeStr
	put property `off` of Period into OffTimeStr
	put property `temp` of Period into Temp
	attach PeriodInfo to `period-info-` cat P
	set the content of PeriodInfo to `ON ` cat OnTimeStr cat ` OFF ` cat OffTimeStr cat `: ` cat Temp cat `&deg;C`
	on click PeriodInfo go to OnClickPeriodInfo
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Parse a HH:MM string in T into minutes-since-midnight.
ParseTime:
	put the value of left 2 of T into HV
	put the value of right 2 of T into MV
	multiply HV by 60 giving T
	add MV to T
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Get the current room set from the map
GetCurrentRooms:
	put property `profiles` of Map into Profiles
	put element CurrentProfile of Profiles into Profile
	put property `rooms` of Profile into Rooms
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Copy the current room set to the map
CopyRoomsToMap:
	put property `profiles` of Map into Profiles
	put element CurrentProfile of Profiles into Profile
	set property `rooms` of Profile to Rooms
	set element CurrentProfile of Profiles to Profile
	set property `profiles` of Map to Profiles
	return

Exit:
	put `{}` into Result
	if Changed
	begin
		put `{}` into RequestData
		set property `action` of RequestData to `roomperiods`
		set property `roomnumber` of RequestData to ClickIndex
		set property `request` of Result to `Update`
		set property `data` of Result to RequestData
	end
	else
	begin
		set property `request` of Result to `Redraw`
	end
	exit
