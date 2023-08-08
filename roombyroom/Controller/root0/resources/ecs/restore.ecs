!	Restore the saved map

	script Restore

    variable Server
    variable MAC

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Restore from backup
Restore:
    put `https://rbr.easycoder.software/rest.php` into Server
    get MAC from storage as `MAC`
    rest post to Server cat `/restore/` cat MAC
    stop
