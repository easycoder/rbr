!	Calendar
!	This drives the Calendar screen. It's called from the Profiles module
!	It does not remain in memory but is loaded and compiled anew each time it is needed.
!	The DOM elements used by this module are already loaded by the Profiles module.

	script Calendar
    
    import div MainPanel
    	and variable Map
        and variable Result

    div ProfileRow
    div ProfileRowText
    div Dialog
    div List
    div DialogRow
    button OKButton
    button HelpButton
    button CancelButton
    button DialogCancelButton
    variable Mobile
    variable Changed
    variable Profile
    variable Profiles
    variable NProfiles
    variable Name
    variable DialogOpen
    variable Day
    variable Calendar
    variable DialogResult
    variable D
    variable P
    
!    debug step
    
    clear Mobile
    if mobile
        if portrait set Mobile
    
	put property `profiles` of Map into Profiles
    
    set the elements of ProfileRow to 7
    set the elements of ProfileRowText to 7

	put 0 into D
    while D is less than 7
    begin
        index ProfileRow to D
        index ProfileRowText to D
        attach ProfileRow to `profile-` cat D
        attach ProfileRowText to `profile-text-` cat D
    	add 1 to D
    end
    on click ProfileRow
    begin
    	gosub to GetProfile
        if DialogResult is not empty
        begin
        	index ProfileRowText to the index of ProfileRow
            set the content of ProfileRowText to DialogResult
            set Changed
        end
    end
    
    put element 0 of Profiles into Profile
    put property `name` of Profile into Name
    put property `calendar-data` of Map into Calendar
    if Calendar is empty
    begin
        put 0 into D
        while D is less than 7
        begin
            index ProfileRowText to D
            set the content of ProfileRowText to empty
            add 1 to D
        end
    end
    else
    begin
        put 0 into D
        while D is less than 7
        begin
            index ProfileRowText to D
            put element D of Calendar into Day
            if Day is `{}` set the content of ProfileRowText to Name
            else set the content of ProfileRowText to property `day` cat D cat `-profile` of Day
            add 1 to D
        end
    end

    attach OKButton to `calendar-ok-button`
    attach HelpButton to `calendar-help-button`
    attach CancelButton to `calendar-cancel-button`
	attach Dialog to `calendar-dialog`
    attach List to `profile-list`
    attach DialogCancelButton to `calendar-dialog-cancel-button`

    on click OKButton
    begin
    	if DialogOpen stop
        if not Changed
        begin
        	set property `request` of Result to `Redraw`
    		exit
        end
        put `[]` into Calendar
        put 0 into D
        while D is less than 7
        begin
            index ProfileRowText to D
            put `{}` into Day
            set property `day` cat D cat `-profile` of Day to the content of ProfileRowText
        	set element D of Calendar to Day
        	add 1 to D
        end
    	set property `request` of Result to `Update`
        set property `data` of Result to Calendar
    	exit
    end
    
    on click HelpButton
    begin
    	set property `request` of Result to `Help`
        set property `data` of Result to `home Calendar`
    	exit
    end

	on click CancelButton
    begin
    	if DialogOpen stop
    	set property `request` of Result to empty
    	exit
    end
    
    put `{}` into Result

	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Choose a profile
GetProfile:
    put the json count of Profiles into NProfiles
    set the elements of Name to NProfiles
    set the elements of DialogRow to NProfiles
    clear List
	put 0 into P
    while P is less than NProfiles
    begin
    	put element P of Profiles into Profile
        index Name to P
        put property `name` of Profile into Name
        index DialogRow to P
        create DialogRow in List
        set style `height` of DialogRow to `1.5em`
        if P modulo 2 set style `background` of DialogRow to `#eee`
        else set style `background` of DialogRow to `#ddd`
        set style `cursor` of DialogRow to `pointer`
        set the content of DialogRow to Name
        add 1 to P
    end
    on click DialogRow
    begin
        put the index of DialogRow into P
		put element P of Profiles into Profile
        put property `name` of Profile into DialogResult
    	set style `display` of Dialog to `none`
    	clear DialogOpen
    end
    set style `display` of Dialog to `flex`
    on click DialogCancelButton
    begin
		put empty into DialogResult
    	set style `display` of Dialog to `none`
    	clear DialogOpen
    end
    set DialogOpen
    while DialogOpen wait 20 ticks
	return