<?php
    // Get statistics.

    function doStatistics($conn, $request)
    {
        $mac = $request[0];
        if (count($request) == 1) {
            // Default: Return total minutes for all rooms
            // Endpoint: {site root}/rest.php/stats/<mac>
            $data = (object)null;
            $result = $conn->query("SELECT * FROM stats WHERE mac='$mac'");
            while ($row = mysqli_fetch_object($result)) {
                $sensor = $row->sensor;
                if (!$data->$sensor) {
                    $data->$sensor = 0;
                }
                $data->$sensor += $row->duration;
            }
            mysqli_free_result($result);
            print('Stats: ');
            print(json_encode($data));
            return;
        }

        $action = $request[1];
        switch ($action) {
            case "month":
                // Return values for every day in a given month
                $y = $request[2];
                $m = $request[3];
                $start = mktime(0, 0, 0, $m + 1, 1, $y);
                $mdays = [31, $y % 4 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 31, 31];
                $monlen = $mdays[$m];
                $days = array();
                for ($n = 0; $n < $monlen; $n++) {
                    $days[$n] = (object)null;
                }
                $finish = $start + $monlen * 24*60*60;
    // print("SELECT * FROM stats WHERE mac='$mac' AND start>=$start AND start<$finish"); print("\n");
                $result = $conn->query("SELECT * FROM stats WHERE mac='$mac' AND start>=$start AND start<$finish");
                while ($row = mysqli_fetch_object($result)) {
                    // print $row->day . " " . $row->sensor . " " . $row->start . " " . $row->duration . "\n";
                    if ($row->duration != 0) {
                        $date = getdate($row->start);
                        $year = $date["year"];
                        $month = $date["mon"];
                        $day = $date["mday"];
                        if ($year == $y && $month == $m + 1) {
                            $d = $days[$day - 1];
                            $d->day = $day;
                            $sensor = $row->sensor;
                            $d->$sensor = $row->duration;
                        }
                    }
                }
                print json_encode($days);
                return;

            case "year":
                // Return data for every month in a given year
                $date = getdate(time());
                $start = mktime(0, 0, 0, $date["mday"], $date["mon"], $date["year"] - 1);
                $months = array();
                for ($n = 0; $n < 12; $n++) {
                    $months[$n] = (object)null;
                }
                $offset = $date["mon"] + 1;
                $result = $conn->query("SELECT * FROM stats WHERE mac='$mac' AND start>$start");
                while ($row = mysqli_fetch_object($result)) {
//                    print $row->sensor . " " . $row->start . " " . $row->duration . "\n";
                    if ($row->duration != 0) {
                        $date = getdate($row->start);
                        $month = $date["mon"] - $offset;
                        if ($month < 0) {
                            $month += 12;
                        }
                        $sensor = $row->sensor;
                        if (!$months[$month]->$sensor) {
                            $months[$month]->$sensor = 0;
                        }
                        $months[$month]->$sensor += $row->duration;
                    }
                }
                print json_encode($months);
                return;
        }
    }

?>
