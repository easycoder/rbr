# Setup Test Sequence

This sequence tests the initial setup of an RBR system from scratch. Each test builds on the state left by the previous one — they must run in order and cannot be run individually.

Run with: `./tests/run-setup-tests.sh`

## setup-01: Smoke Tests

Verifies the basic infrastructure works:

- Page loads with correct title ("RBR UI")
- AllSpeak runtime loads and compiles rbr.as
- MQTT connects to the local broker
- Main screen renders (Webson DOM is built)
- Banner shows "Room By Room"
- Key UI elements are present (main panel, system name, profile button, hamburger, logo)
- Subtitle text is correct
- No JavaScript errors on load

## setup-02: System Name

Renames the system from the default name.

- Verifies system name shows "New System" (from template map)
- Opens the hamburger menu
- Clicks "Set the system name"
- Types "RBR Test System" into the input
- Clicks OK
- Verifies system name updates to "RBR Test System"

## setup-03: Profile Name

Renames the default profile.

- Verifies profile button shows "Default"
- Clicks the profile button to open the profiles page
- Clicks the edit icon on the first profile
- Types "Normal" into the rename dialog
- Clicks OK to confirm the rename
- Clicks OK to save and exit the profiles page
- Verifies profile button shows "Normal" on the main screen

## setup-04: Add Room

Adds the first room to an empty system.

- Verifies no rooms are shown initially
- Opens the hamburger menu
- Clicks "Add a room"
- Verifies a room row appears with the name "Unnamed"
- Verifies room elements are present (temperature display, edit icon, status indicator)
- Verifies system name shows "RBR Test System"
- Verifies only one room exists (no duplicates)

## setup-05: Rename Kitchen

Renames the first room from "Unnamed" to "Kitchen".

- Verifies the room shows "Unnamed"
- Clicks the edit icon on the room row
- Clicks "Edit this room" in the room tools menu
- Clicks "Edit the room name" in the room editor
- Types "Kitchen" into the rename dialog
- Clicks OK
- Verifies the room name updates to "Kitchen"

## setup-06: Kitchen Devices

Assigns a thermometer and radiator to the Kitchen.

- Verifies the room shows "Kitchen"
- Clicks the edit icon on the room row
- Clicks "Edit this room" in the room tools menu
- Clicks "Edit device parameters" in the room editor
- Sets the sensor ID to "Kitchen-thermometer"
- Selects relay type "Zigbee" from the dropdown
- Sets the relay address to "Kitchen-radiator"
- Checks the "linked" checkbox (sensor is linked to relay)
- Clicks Save
- Verifies the room is still displayed correctly

## setup-07: Living Room

Adds, renames, and configures the Living Room.

- Verifies Kitchen is showing at index 0
- Adds a new room via the hamburger menu
- Verifies "Unnamed" appears at index 1
- Renames it to "Living Room" via edit icon > Edit this room > Edit the room name
- Configures devices: sensor "Living-Room-thermometer", relay type "Zigbee", relay "Living-Room-radiator", linked
- Verifies both Kitchen and Living Room are displayed (2 rooms total)

## setup-08: Add Temporary Room

Adds a temporary room that will be deleted later, testing the add/delete cycle.

- Verifies Living Room is showing at index 1
- Adds a new room via the hamburger menu
- Verifies "Unnamed" appears at index 2
- Verifies 3 rooms total

## setup-09: Main Bedroom

Adds, renames, and configures the Main Bedroom.

- Verifies the temporary "Unnamed" room is at index 2
- Adds a new room via the hamburger menu
- Verifies "Unnamed" appears at index 3
- Renames it to "Main Bedroom" via edit icon > Edit this room > Edit the room name
- Configures devices: sensor "Main-Bedroom-thermometer", relay type "Zigbee", relay "Main-Bedroom-radiator", linked
- Verifies all four rooms are displayed in order (Kitchen, Living Room, Unnamed, Main Bedroom)

## setup-10: Guest Bedroom

Adds, renames, and configures the Guest Bedroom.

- Verifies Main Bedroom is showing at index 3
- Adds a new room via the hamburger menu
- Verifies "Unnamed" appears at index 4
- Renames it to "Guest Bedroom" via edit icon > Edit this room > Edit the room name
- Configures devices: sensor "Guest-Bedroom-thermometer", relay type "Zigbee", relay "Guest-Bedroom-radiator", linked
- Verifies all five rooms are displayed in order (Kitchen, Living Room, Unnamed, Main Bedroom, Guest Bedroom)

## setup-11: Delete Temporary Room

Deletes the temporary "Unnamed" room added in setup-08.

- Verifies all 5 rooms are present, with "Unnamed" at index 2
- Clicks the edit icon on the temporary room
- Clicks "Delete this room" in the room tools menu
- Confirms deletion by clicking "Yes" in the dialog
- Verifies 4 rooms remain
- Verifies the correct rooms in order: Kitchen, Living Room, Main Bedroom, Guest Bedroom

## setup-12: Room Schedules

Sets timing schedules for all four rooms and switches them to timed mode.

**Kitchen** (6 periods):
- from 07:00: 21.0°C
- from 09:00: 15.0°C
- from 12:30: 21.5°C
- from 14:00: 15.0°C
- from 18:00: 22.0°C
- from 20:00: 15.0°C

**Living Room** (2 periods):
- from 18:00: 24.0°C
- from 23:00: 15.0°C

**Main Bedroom** (4 periods):
- from 07:00: 21.0°C
- from 09:00: 15.0°C
- from 22:30: 23.0°C
- from 23:30: 15.0°C

**Guest Bedroom** (4 periods):
- from 07:00: 21.0°C
- from 09:00: 15.0°C
- from 22:30: 22.0°C
- from 23:30: 15.0°C

After setting schedules, each room is switched to "timed" mode via the mode dialog.
