    script Test

    variable Value

    get Value from url `https://eclecity.net/index.html`
    on failure
    begin
        log `Failed`
        set Value to `Failed`
    end
    log Value

    download `https://rbrheating.com/controller.as` to `controller.as.new`
        on failure
        begin
            log `Update aborted: download of controller.as failed`
            return
        end
    exit

