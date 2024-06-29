# Complete project details at https://RandomNerdTutorials.com

def web_page():
  if led.value() == 1:
    gpio_state="ON"
  else:
    gpio_state="OFF"
  
  html = """<html><head> <title>ESP Web Server</title> <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,"> <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
  h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none; 
  border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
  .button2{background-color: #4286f4;}</style></head><body> <h1>ESP Web Server</h1> 
  <p>GPIO state: <strong>""" + gpio_state + """</strong></p><p><a href="/?led=on"><button class="button">ON</button></a></p>
  <p><a href="/?led=off"><button class="button button2">OFF</button></a></p></body></html>"""
  return html

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
  conn, addr = s.accept()
  print('Got a connection from %s' % str(addr))
  request = conn.recv(1024)
  request = str(request)
  print('Content = %s' % request)
  led_on = request.find('/?led=on')
  led_off = request.find('/?led=off')
  if led_on == 6:
    print('LED ON')
    led.value(1)
  if led_off == 6:
    print('LED OFF')
    led.value(0)
  response = web_page()
  conn.send('HTTP/1.1 200 OK\n')
  conn.send('Content-Type: text/html\n')
  conn.send('Connection: close\n\n')
  conn.sendall(response)
  conn.close()


View raw code

The script starts by creating a function called web_page(). This function returns a variable called html that contains the HTML text to build the web page.

def web_page():
The web page displays the current GPIO state. So, before generating the HTML text, we need to check the LED state. We save its state on the gpio_state variable:

if led.value() == 1:
  gpio_state="ON"
else:
  gpio_state="OFF"
After that, the gpio_state variable is incorporated into the HTML text using “+” signs to concatenate strings.



html = """<html><head> <title>ESP Web Server</title> <meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,"> <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none; 
border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
.button2{background-color: #4286f4;}</style></head><body> <h1>ESP Web Server</h1> 
<p>GPIO state: <strong>""" + gpio_state + """</strong></p><p><a href="/?led=on"><button class="button">ON</button></a></p>
<p><a href="/?led=off"><button class="button button2">OFF</button></a></p></body></html>"""
Creating a socket server
After creating the HTML to build the web page, we need to create a listening socket to listen for incoming requests and send the HTML text in response. For a better understanding, the following figure shows a diagram on how to create sockets for server-client interaction:

python socket server and client

Create a socket using socket.socket(), and specify the socket type. We create a new socket object called s with the given address family, and socket type. This is a STREAM TCP socket:




s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
Next, bind the socket to an address (network interface and port number) using the bind() method. The bind() method accepts a tupple variable with the ip address, and port number:

s.bind(('', 80))
In our example, we are passing an empty string ‘ ‘ as an IP address and port 80. In this case, the empty string refers to the localhost IP address (this means the ESP32 or ESP8266 IP address).

The next line enables the server to accept connections; it makes a “listening” socket. The argument specifies the maximum number of queued connections. The maximum is 5.

s.listen(5)
In the while loop is where we listen for requests and send responses. When a client connects, the server calls the accept() method to accept the connection. When a client connects, it saves a new socket object to accept and send data on the conn variable, and saves the client address to connect to the server on the addr variable.

conn, addr = s.accept()
Then, print the address of the client saved on the addr variable.

print('Got a connection from %s' % str(addr))
The data is exchanged between the client and server using the send() and recv() methods.

The following line gets the request received on the newly created socket and saves it in the request variable.



request = conn.recv(1024)
The recv() method receives the data from the client socket (remember that we’ve created a new socket object on the conn variable). The argument of the recv() method specifies the maximum data that can be received at once.

The next line simply prints the content of the request:

print('Content = %s' % str(request))
Then, create a variable called response that contains the HTML text returned by the web_page() function:

response = web_page()
Finally, send the response to the socket client using the send() and sendall() methods:

conn.send('HTTP/1.1 200 OK\n')
conn.send('Content-Type: text/html\n')
conn.send('Connection: close\n\n')
conn.sendall(response)
In the end, close the created socket.

conn.close()
Testing the Web Server
Upload the main.py and boot.py files to the ESP32/ESP8266. Your device folder should contain two files: boot.py and main.py.



After uploading the files, press the ESP EN/RST on-board button.

esp32 enable button

After a few seconds, it should establish a connection with your router and print the IP address on the Shell.



Open your browser, and type your ESP IP address you’ve just found. You should see the web server page as shown below.

esp32 web server control outputs



When you press the ON button, you make a request on the ESP IP address followed by /?led=on. The ESP32/ESP8266 on-board LED turns on, and the GPIO state is updated on the page.

Note: some ESP8266 on-board LEDs turn on the LED with an OFF command, and turn off the LED with the ON command.

web server on smartphone and esp32



When you press the OFF button, you make a request on the ESP IP address followed by /?led=off. The LED turns off, and the GPIO state is updated.



Note: to keep this tutorial simple, we’re controlling the on-board LED that corresponds to GPIO 2. You can control any other GPIO with any other output (a relay, for example) using the same method. Also, you can modify the code to control multiple GPIOs or change the HTML text to create a different web page.

Wrapping Up
This tutorial showed you how to build a simple web server with MicroPython firmware to control the ESP32/ESP8266 GPIOs using sockets and the Python socket library. If you’re looking for a web server tutorial with Arduino IDE, you can check the following resources:

ESP32 Web Server – Arduino IDE
ESP8266 Web Server – Arduino IDE


If you’re looking for more projects with the ESP32 and ESP8266 boards, you can take a look at the following:

20+ ESP32 Projects and Tutorials
30+ ESP8266 Projects
We hope you’ve found this article about how to build a web server with MicroPython useful. To learn more about MicroPython, take a look at our eBook: MicroPython Programming with ESP32 and ESP8266.




SMART HOME with Raspberry Pi ESP32 and ESP8266 Node-RED InfluxDB eBook
SMART HOME with Raspberry Pi, ESP32, ESP8266 [eBook]
Learn how to build a home automation system and we’ll cover the following main subjects: Node-RED, Node-RED Dashboard, Raspberry Pi, ESP32, ESP8266, MQTT, and InfluxDB database DOWNLOAD »
Recommended Resources

Build a Home Automation System from Scratch » With Raspberry Pi, ESP8266, Arduino, and Node-RED.


Home Automation using ESP8266 eBook and video course » Build IoT and home automation projects.


Arduino Step-by-Step Projects » Build 25 Arduino projects with our course, even with no prior experience!

What to Read Next…
ESP32 with RCWL-0516 Microwave Radar Proximity Sensor Arduino IDE
ESP32 with RCWL-0516 Microwave Radar Proximity Sensor (Arduino IDE)
ESP32 Client-Server Wi-Fi Communication Between Two Boards
ESP32 Client-Server Wi-Fi Communication Between Two Boards

ESP8266 – Wireless Weather Station with Data Logging to Excel

Enjoyed this project? Stay updated by subscribing our newsletter!
Your Email Address

SUBSCRIBE
100 thoughts on “ESP32/ESP8266 MicroPython Web Server – Control Outputs”

Henk Oegema
November 1, 2018 at 12:17 pm
Thanks very much for this article. This was exactly what I was looking for.
Would also appreciate an article about sending e-mail with micro python from an esp8266.

Reply

Domenico Carvetta
November 1, 2018 at 5:05 pm
Great Rui, I stay tuned , bye Domenico

Reply

Maurizio Cozzetto
November 1, 2018 at 5:37 pm
Great! Keep going on!

Reply

Stefan
November 1, 2018 at 5:48 pm
Hello Sara,

this explanation is pretty detailed. IMHO it is a good compromise between explaining it all from scratch and “drop a short textline”

I want to make some suggestions how to improve the explanation.
Add “ESP32” to word “server” and the words “your smartphone, tablet or PC” to the word “client” at the grafic which shows the steps what server and client are doing.

The result a webpage that can be clicked to switch on/off a LED is impressing. To achieve this a lot of code-technologies have to be used. I don’t want to suggest explain all
– server-client,
– TCP/IP,
– sockets,
– HTML
all from scratch. That would inflate the explanation much too much.

But there are a few places where a small effort gives pretty much more insight into using all these coding-technologies.

I mean find a way that the parts of the html-code that defines the buttons and the text on the buttons is very easy to find and easy to modify.

Another way could be using some kind of a website-editor, if there exists one that is easy to use. By “easy to use” I mean a software that is very very similar to an office-software or at least very very intuitive to use.
So that one hour of learning is enough to create a website-variation of your demo that has three buttons and a slider.

Then showing how the html-code-output of this software is implemented into the python-code by copy and paste.

best regards

Stefan

Reply

Sara Santos
November 2, 2018 at 2:32 pm
Hi Stefan.
Thank you for your suggestions. We’ll take those into account when writing new posts about this subject.
Also, I’ll try to improve this article when I have the chance.
Thank you.
Regards,
Sara 🙂

Reply

Fourchtein
November 2, 2018 at 9:27 am
Thanks
Great
Philippe

Reply

Sara Santos
November 2, 2018 at 2:32 pm
Thanks 🙂

Reply

Bernard
November 2, 2018 at 2:45 pm
Hi Rui,
I have Linux Mint 19 based on ubuntu … uPyCraft IDE doesn’t work … Is there another way or an improvement pf uPyCraft IDE ?
Thank you

Reply

Sara Santos
November 2, 2018 at 2:47 pm
Hi Bernard.
uPyCraft should work on your system if you compile it yourself: github.com/DFRobot/uPyCraft_src
If you compile it, it should work.
Note: you don’t need to use uPycraft IDE, you can program program the board with a serial connection using REPL or webREPL.
Regards,
Sara 🙂

Reply

paulo
December 14, 2020 at 2:58 pm
Use Thonny, is much easier.

Reply

Giovanni
November 3, 2018 at 6:05 pm
Dear, I’have a lot of problem to use this app with Safari or Google Chrome for iPhone. If I use Google Chrome for mac I don’t have any problem, but when I use Safari I can’t open the page. I see the serial, and I can read the connection by computer to ESP32, but the browser don’t open the contents. Also on Android and Google Chrome all works.

Reply

Sara Santos
November 4, 2018 at 11:35 am
Hi Giovanni.
I’m sorry to hear that.
I actually didn’t test the web server on Safari or iPhone. I’ll try to figure out what happens.
Meanwhile, if you find what causes the problem, just let us know.
Regards,
Sara 🙂

Reply

bob
November 4, 2018 at 4:27 pm
good article as usual 🙂
My question though is why or when would you use python instead of the Arduino ide? What are the benefits etc.
Also I agree with Stefan on the editor HTML thing might be helpful.

Reply

Sara Santos
November 8, 2018 at 9:44 am
Hi Bob.
I think both are good ways to program the ESP32.
MicroPython is much simpler to program, it supports a REPL (Read-Evaluate-Print Loop). The REPL allows you to connect to a board and execute code quickly without the need to compile or upload code.
It also gives you a better overview of the files stored on the ESP32. Uploading code to the ESP32 is much faster with MicroPython.
In terms of libraries for sensors and modules, at the moment there is more support for Arduino IDE.
Regards,
Sara 🙂

Reply

Bob Willemen
December 4, 2018 at 2:04 pm
Works perfect on my old laptop ( Ubuntu ) using Chromium or Firefox . Doesn’t work on my IPhone 5S ( tried Safari and Chromium ) . EFM ( electronics F…… magic) ..
Thanks anyway , great tutorial , step by step explained , Great Job !
Bob

Reply

Bob Willemen
December 4, 2018 at 2:26 pm
I made a printscreen with the result of “request = conn.recv(1024)” . First logon is the laptop , 2nd one is the Phone . I can mail it if you want it . Thanks again , keep up the good job !
Bob

Reply

Sara Santos
December 5, 2018 at 5:56 pm
Hi Bob.
Thank you.
You can send your results using our contact form: https://randomnerdtutorials.com/contact/
Regards,
Sara

Reply

Bob Willemen
December 6, 2018 at 1:54 pm
Hi Sara , thx for the quick reply ! How can I submit a .png file ( printscreen from a Linux screen session )?
Thx , many greetings from Belgium ,
Bob

Reply

Sara Santos
December 7, 2018 at 11:44 am
Hi Bob.
You can upload the image using https://imgur.com/ and then paste the link.
Regards,
Sara

Reply

Bob Willemen
December 5, 2018 at 1:39 pm
Did Some research and tried different browsers on my. IPhone .
Puffin browser replied : Error 102
(net:: ERR_CONNECTION_REFUSED) when loading URL http://(IP-adress)
Hope this is a clue ….
Thanks a lot and keep up the good job !
Bob

Reply

Michael Zwicky-Ross
December 6, 2018 at 8:02 pm
I think I followed the steps correctly but when I try to run it I get error messages:

main.py:4: undefined name ‘led’
main.py:18: undefined name ‘socket’
main.py:18: undefined name ‘socket’
main.py:18: undefined name ‘socket’
main.py:32: undefined name ‘led’
main.py:35: undefined name ‘led’

Any suggestions what I’m doing wrong?

Thank you.

Reply

Sara Santos
December 7, 2018 at 11:30 am
Hi Michael.
I think you’re getting those error because you haven’t uploaded the boot.py file to the ESP32.
https://github.com/RuiSantosdotme/Random-Nerd-Tutorials/blob/master/Projects/ESP-MicroPython/esp_web_server_boot.py

I hope this helps.
Regards,
Sara 🙂

Reply

Dave
March 31, 2019 at 10:38 pm
I am getting the same problem even after using code in your book, I bought last week, and at github.
I am not sure how esp_web_server_main.py gets socket and led from esp_web_server_boot.py?
uPyCraft shows both these files only under device.

Reply

Sara Santos
April 1, 2019 at 9:03 am
Hi Dave.
If you’re having problems with our course, I recommend that you post a question in our forum – that’s where we give support to our costumers.
The files should have the following names: main.py, and boot.py (it will not work if they are called esp_web_server_main.py or esp_web_server_boot.py using uPycraft IDE).
Can you post your doubts, problems and questions here: https://rntlab.com/forum/
Thank you
Regards,
Sara

Reply

Bob Willemen
December 10, 2018 at 10:01 am
Found a working script for the IPhone , out of the box from the official micropython site :
https://docs.micropython.org/en/latest/esp8266/tutorial/network_tcp.html#simple-http-server
I modified boot.py a little ( removed double imports ) , works perfect 🙂
these lines ( “arduino style”) make the difference I think …
line = cl_file.readline()
if not line or line == b’\r\n’:
Anyway , thanks a lot for helping people to become decent programmers 🙂
Love you guys , lots of greetings from Belgium ,
Bob

Reply

Sara Santos
December 14, 2018 at 5:24 pm
Hi Bob.
That’s great!
Thank you so much for sharing and for supporting our work.
Regards,
Sara 🙂

Reply

Jaroslav Kadlec
December 23, 2018 at 3:43 pm
Hi Rui,
I’m a complete beginner and I’m not sure why the code appears
if led_on == 6:
Why is there number 6?

Reply

Sara Santos
December 26, 2018 at 5:17 pm
Hi Jaroslav.
In the while loop, after receiving a request, we need to check if the request contains the ‘/?led=on’ or ‘/?led=on’ expressions. For that, we can apply the find() method on the request variable. the find() method returns the lowest index of the substring we are looking for.

Because the substrings we are looking for are always on index 6, we can add an if statement to detect the content of the request. If the led_on variable is equal to 6, we know we’ve received a request on the /?led=on URL and we turn the LED on.
If the led_off variable is equal to 6, we’ve received a request on the /?led=off URL and we turn the LED off.

I hope my explanation is clear.
Regards,
Sara 🙂

Reply

Hans Pettersson
February 13, 2019 at 10:01 am
Hi
Many thanks for your work
Following this article works fine. But there is tow questions
The program stops at “conn, addr = s.accept()” waiting for a request, and it can wait for ever.
Is it possible just to check if there is one and if there is not continue the loop and the check again the next loop. If this is possible you can use the micro controller for other task in between the requests as in the Arduino env
When connecting with Chrome, on PC or phone, the connection are busy for ever if you do not close the browser
The server hangs printing Got a connection from (‘192.168.1.193’, 54536) and you can not use any other computer or browser untill it is closed, not just the tab but the whole browser.
Connecting the a Raspberry pi works fine.
As it works on RPi it seems to be the PC/phone or Chrome that is the problem. Is there something to do about this. It happen that you forget to close the window and then is it impossible to aces the serve from an other place

Reply

Sara Santos
February 17, 2019 at 11:00 am
Hi Hans.
You are right.
But I don’t think it is something to do with the code. Because when we first implemented this, it worked fine supporting several clients at the same time.
It seems that google Chrome opens two connections, leaving the second one opened. So we are not able to listen requests from other clients while that connection is opened.
I don’t know why this is happening, but we’re working to find a solution.
If you know a workaround for this, please share with us.
Thank you for your comment.
Regards,
Sara

Reply

Juergen
June 13, 2021 at 5:10 am
Dear Sara,
thanks for the great tutorial it helped me a lot.

I have the same issue with like Hans explained:
“The program stops at “conn, addr = s.accept()” waiting for a request, and it can wait for ever.”

Is there a chance to check the content of s.accept() and branch out in case of “empty”.
I need to measure temperature and show to a display in as well.

thanks Juergen

Reply

Luke
August 26, 2021 at 7:35 pm
Hi Juergen, or anyone else wishing to achieve the same… temperature and screen refresh as a timer loop on my ESP32, so this runs at the same time as the loop waiting for requests.

I am also however currently struggling with google chrome especially as my script doesn’t always generate a response, it will often error closing the connection without a response being sent.

would be interested if anyone has found a solution to this, I will try and update if i do myself.

Reply

Jürgen
August 27, 2021 at 6:04 am
Hi Sara, Luke, all,

i have it solved in following way:
– created a ISR (interupt service routine) triggered by machine.timer(0)
– f.e. each 2 seconds the routine is stepping out performing my requested task and returning to the accept() position

Init code:

#Timer Interrupt
tim0 = machine.Timer(0)
tim0.init(period=2000, mode=machine.Timer.PERIODIC, callback=handle_callback)

Main code:

Timer Interrupt Routine

def handle_callback(timer):
….# your functions to call

I’m surprised how good that works; might it’s not professional, but it is doing what it should.

kind regards
Jürgen


Luke
August 27, 2021 at 12:14 pm
Jurgen / All,

I done this the same way using the timer to update my screen, works great for me.. I was also working on this for while yesterday and discovered a few things which have made a big difference in the reliably if receiving a response (tested on Chrome for Windows and Android).

Used the replay method from the Micropython.org example as mentioned by Bob in a previous comment:
response = HTML
conn_file = conn.makefile(‘rwb’, 0)
conn.send(‘HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n’)
conn.send(response)
conn.close()

Used _Thread to run multiple threads with s.accept. I put the whole Socket Script into a Function and call it from both a secondary and main thread. I actually found this on a tutorial for the Pi Pico, but it worked fine on my ESP32.
import _thread

I’m so glad to see these comments are still ative.


Joseph Tannenbaum
October 29, 2019 at 9:34 pm
As usual, this was a great tutorial. Took me a couple of times to get it to come together. I have a Heltec wifi 32 with oled and wanted the oled to tell me what ip I was connected to. Has anyone else complained that the Upycraft ide crashes windows 10?

Reply

Sara Santos
October 30, 2019 at 9:31 am
Hi Joseph.
If you have frequent crashes with upycraft IDE, I suggest you experiment Thonny IDE.
You can follow our tutorial and see if you like this IDE better: https://randomnerdtutorials.com/getting-started-thonny-micropython-python-ide-esp32-esp8266/
Regards,
Sara

Reply

Joseph Tannenbaum
October 30, 2019 at 4:13 pm
Tried it, but like the Upycraft because you can see the files in the espxxxx. Also Thonny has updated since your tutorial and the commands under the ‘device’ are not there. It’s a lot more awkward to use for me. Been trying Rshell on a Pi to program the modules. Not too bad except I don’t have much space to set it up.

Reply

Joseph Tannenbaum
December 20, 2019 at 9:47 pm
Got Thonny working, but the second time you modify a file and tried to re save it to the module, Thonny goes berserk and crashes. Actually using the Raspberry Pi is easier once it is set up.

Reply

Marin
November 24, 2019 at 2:24 pm
Hi Sara,
Wonderful tutorial, thanks!

Reply

Sara Santos
November 24, 2019 at 3:23 pm
Thanks 😀

Reply

Christian
December 24, 2019 at 9:54 am
Hi Sara,

great Tutorial. Thanks.

Reply

John Helliwell
January 30, 2020 at 2:49 pm
Hi Sara, Rui
Thanks so much for this tutorial. I tried it as it out as my first project after I setup my ESP32 with micropython. The code is beautifully explained and worked first time for me

John

Reply

Sara Santos
January 30, 2020 at 3:03 pm
Hi John.
That’s great!
Regards,
Sara

Reply

Julien
February 4, 2020 at 11:09 am
Hello Sara,

I cannot connect to the server. I am using a Mobile shared connection of Android

When I type ifconfig in the Micropython Terminal I have the following error message :
NameError: name ‘ifconfig’ isn’t defined

When I add :
“print(‘Connection successful’)
print(station.ifconfig())”
to the main.py and run the code I get this message error :
NameError: name ‘station’ isn’t defined

Thanks for your help and good nob by the way the tuto is nice
Cheers
Julien

Reply

Sara Santos
February 4, 2020 at 12:03 pm
Hi Julien.
Have you uploaded the boot.py file before? The boot.py imports the required libraries and that seems to be an issue regarding not having the libraries imported.
Make sure you upload the boot.py first or that you copy all the content of the boot.py file to the main.py file to make it work.
I hope this helps.
Regards,
Sara

Reply

Julien
February 5, 2020 at 3:51 pm
Hi Sarah, I have try again with the boot inside my main.py and it seems to works except that the REPL does not write any IP adresse (Once more I am on cellphone hotpost) and “connection successful” but something unwridable :

dc|{cc’ndoo#p$sl{dxnlcg|dcnn

I use a ESP8266 D1 mini and upycraft. And thanks a lot for your previous fast answer !

Cheers
Julien

Reply

Julien
February 5, 2020 at 4:06 pm
Sorry, please do not consider previous comment. It works when I put on the REPL “print(station.ifconfig())” and it give me the following answer :

(‘0.0.0.0’, ‘0.0.0.0’, ‘0.0.0.0’, ‘xxx.xx.222.222’)

then I upload my code and I pres RST on board button I get the following message :
`

but no esp IP adress

Can you help me ?
thanks
Julien

Reply

Sara Santos
February 5, 2020 at 5:00 pm
Hi Julien.
I don’t know what might be wrong.
With the current code in your board, can you run the commands shown here on the shell :http://docs.micropython.org/en/v1.8.7/esp8266/esp8266/tutorial/network_basics.html#network-basics
and tell me what you get?
Regards,
Sara


Sara Santos
February 5, 2020 at 4:51 pm
Hi Julien.
Once the code is successfully uploaded, press the ESP8266 reset button and see if it prints the IP address.
Regards,
Sara

Reply

Steve Cornish
February 11, 2020 at 8:29 pm
Hi Sara

An excellent tutorial. I used Thonny as the IDE as uPyCraft was causing me problems. However i did have a issue:

NameError: name ‘led’ isn’t defined
NameError: name ‘socket’ isn’t defined

This I believe is due to the boot.py and main.py are not running in the same namespace which I assume is Thonny 3.2.7 issue. Any thoughts on this?
NameError: na me ‘led’ isn’t defined
NameError: name ‘socket’ isn’t defined

I solved the problem by moving everything in the boot.py apart from
import uos, machine
import gc
gc.collect()

into the main.py

Note with Thonny you have to use “Stop” button before “run the current script” again or you get a OSError: [Errno 98] EADDRINUSE

Regards
Steve

Reply

Eduardo Carlos
February 16, 2020 at 12:18 am
Hi Sara
I have some problems whit the code. I’m using uPycraft v1.0 and when I teste the code in main.py, some lines are wrong. I don’t know if this problem is due the version of the program. And other problem with Testing the Web Server; when I press the EN buttom, my esp32 lose the firmware and can’t create the web server. When I check the sintax, this problems come up

*main.py:2: undefined name ‘led’
*main.py:16: undefined name ‘socket’
*main.py:16: undefined name ‘socket’
*main.py:16: undefined name ‘socket’
*main.py:30: undefined name ‘led’
*main.py:33: undefined name ‘led’
syntax finish.

Thank’s very much.
Eduardo

Reply

Sara Santos
February 16, 2020 at 10:51 am
Hi Eduardo.
Make sure that you also uploaded the boot.py file that contains initialization for the led and socket.
Regards,
Sara

Reply

Eduardo Carlos
February 16, 2020 at 10:45 pm
I tried, but it does not function. The message ‘ Connection successful
(‘192.168.4.1’, ‘255.255.255.0’, ‘192.168.4.1’, ‘0.0.0.0’) ‘ does not show up. When I press the EN button the firmware is deleted. I tried the MicroPython: ESP32/ESP8266 Access Point (AP) tutorial, and this got right.
Regards,
Eduardo

Reply

Vikram Meher
February 18, 2020 at 6:42 am
Was able to do it with a little hiccup but managed to run it quickly .. Thanks for the nice tutorial.

Reply

Sara Santos
February 18, 2020 at 10:27 am
Great ;D

Reply

JC`zic
February 18, 2020 at 10:30 pm
Great There is also a nice web server on MicroPython that also allows you to do “real-time” with WebSockets :
v1 : github.com/jczic/MicroWebSrv
v2 : github.com/jczic/MicroWebSrv2 (new)
🙂

Reply

Sara Santos
February 20, 2020 at 10:51 am
Hi.
Thank you for sharing your libraries.
We’ll take a look at them in a near future 😀
Regards,
Sara

Reply

Ian M
March 13, 2020 at 4:40 pm
I’m curious about how to use usocket with a slider, to pass the value to a function. I’m looking to change the PWM duty cycle through that, to control the brightness of an LED.

Reply

Sara Santos
March 15, 2020 at 4:48 pm
Hi Ian.
At the moment, we don’t have any tutorial for that.
We have a tutorial just for PWM: https://randomnerdtutorials.com/esp32-esp8266-pwm-micropython/
Regards,
Sara

Reply

Ian Marvin
March 24, 2020 at 2:19 pm
I managed to work out a way of doing what I wanted. The issue I had to tackle was that the HTML button causes the page to reload, meaning that the slider resets to defaults, I wanted it to stay the same. Using a short script and ‘onclick’ for the buttons and ‘oninput’ for the slider I can get it to work without reloading. The xhttp function can then pass a value to the rest of the python script which can then be parsed to control, in my case, 4 channels of lighting with the slider working as a dimmer. Even once you have set the colour mix from the buttons, the slider will act as a simple dimmer. I can share code for this, although it’s probably a bit untidy now. I made the HTML part a separate file, also the lightcontrol function.

Reply

Sara Santos
March 24, 2020 at 3:20 pm
Hi Ian.
Thanks for your comment.
You can share your code. It might be useful for our readers.
Use pastebin preferably to share the code. You can see the instructions here: https://rntlab.com/question/need-help-using-pastebin/
Thank you 😀
Regards,
Sara

Reply

Gil
March 30, 2022 at 11:46 am
Hi, I’m trying to accomplish the same goal of getting values without having to reload. Would you mind uploading your code to the pastebin Sara commented about? I think if I can even just see the code, that would be enough for me to reverse engineer it (though if you want to include an explanation, I wouldn’t mind that either haha).

Thanks!!

Reply

Bruno Westermann
April 10, 2024 at 9:35 pm
Could you provide your Code for that i think it would be of interest for a lot of people.

Reply

Fritz
May 5, 2020 at 1:10 pm
Hello,

Great tutorial. I’ve been playing around with this Tuto and the one with relays/webserver. Everything works, when i browse to the web server address and the on/off buttons work. But the problem is that I’m unable to view the web server page from a mobile device.

Do you have an suggestions?

Reply

Sara Santos
May 6, 2020 at 2:41 pm
Hi.
Are you using an ESP32 or ESP8266?
Regards,
Sara

Reply

Steve Cornish
July 9, 2020 at 6:33 pm
Non-Blocking connection
What i would like to do is to do an analogue read and update the web page with its value. However the current code waits for a connection before before carrying out any action so a pot_value = pot.read() will only get carried out one the web page a GET is executed. Does anyone have any idea how to get micropython to check for a connection i.e. GER#T sent and if not then to continue to foe example read the analogue value and update the web page. I can do this easily in Arduino with webSocket.onEvent(webSocketEvent). Is there an equivalent in micropython
Thank you Steve

Reply

Jack
July 29, 2020 at 9:58 pm
Just dropping some love for this tutorial in 2020. Everything works, and I’m super happy I learned about UPyCraft. Thanks!!!

Reply

YASH PATEL
August 27, 2020 at 6:13 am
As per the tutorial, I copy boot.py into ESP32.
Now I could not connect my ESP32 with any IDE.

I got error like,

Device is busy or does not respond. Your options:

wait until it completes current work;
use Ctrl+C to interrupt current work;
use Stop/Restart to interrupt more and enter REPL.

────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Could not enter REPL. Trying again with 1 second waiting time…
Could not enter REPL. Trying again with 3 second waiting time…
Could not enter REPL. Trying again with 5 second waiting time…
Could not enter REPL. Giving up. Read bytes:
b”

Your options:

check connection properties;
make sure the device has suitable firmware;
make sure the device is not in bootloader mode;
reset the device and try again;
try other serial clients (Putty, TeraTerm, screen, …);
ask for help in Thonny’s forum or issue tracker.

Backend terminated or disconnected. Use ‘Stop/Restart’ to restart.

I couldn’t find any solution.
I want to factory reset or change boot.py file but my ESP32 never go into boot mode.

if you have any solution please let me know.
Thank You.

Reply

Sara Santos
August 27, 2020 at 4:52 pm
Hi.
Try erasing the flash and start the project again.
https://rntlab.com/question/how-perform-reset-factory-esp32/
Regards,
Sara

Reply

YASH PATEL
August 28, 2020 at 6:00 am
Thank you for your reply.
ESP32 detected in Device manager on COM7 but not detected on esptool.
error is,
‘esptool.py’ is not recognized as an internal or external command,
operable program or batch file.
Regards,
Yash Patel

Reply

Philip Hart
September 18, 2020 at 5:43 am
Hi,
I get this error too with ESP32 boards, but very rarely with ESP8266.
I read somewhere that the ESP32/MicroPython thing isn’t as mature or stable yet, so that could be the problem.
In fact, have 4 ESP32 boards and while they are all fine with Arduino, only one of them (from M5Stack) works reliably with MicroPython.
Seems the cheap clones are more prone to giving this error. My solution – buy branded boards (M5Stack, DFrobot etc) or use ESP8266
Hope that helps

Reply

Chris
April 9, 2021 at 8:52 am
Hi Sara! Thanks for this great tutorial. Is there a way that this functionality could be extended so that the ESP32 could listen for requests on a non-local address, i.e. a post request to http://myserver.com/endpoint ?

Reply

Till
July 4, 2021 at 6:49 pm
The tutorial states that garbage collection frees up flash memory:

“This is useful to save space in the flash memory”

This is not true. Garbage collection happens as runtime and affects ram only.

Reply

Sara Santos
July 5, 2021 at 10:19 am
Thanks for the clarification 🙂

Reply

JackRay
September 16, 2021 at 1:36 pm
Hello Sara,
your job is very well done, I admire your simplicity in explaining complex things.

I created a Tkinter interface to drive all my iTOs with a raspberry, and I cannot directly send my instrauctions from my raspberry to my esp8266.

my project is to set up a weather station and, depending on the data, retrieve from the web, open or close the shutters of the house.

For example .

Thanks for your help

Cdlt.

JackRay

Reply

Sara Santos
September 17, 2021 at 9:22 am
Hi.
What protocol are you using to send data from the RPi to the ESP8266?
Regards,
Sara

Reply

Jahidul Islam Rahat
October 12, 2021 at 7:48 am
if led_on == 6:
print(‘LED ON’)
led.value(1)
if led_off == 6:
print(‘LED OFF’)
led.value(0)
why we use 6 in every condition?

Reply

Sara Santos
October 12, 2021 at 9:44 am
Hi.
Here’s the answer: https://rntlab.com/question/index-6/
Regards,
Sara

Reply

Henry
October 20, 2021 at 4:24 pm
Hi, thanks for the detailed tutorial. I’m using the esp32. I think I may have a bug. I get a “TypeError: object with buffer protocol required” error message for the “conn.sendall(response)” line at the end of the main.py code. I’m using MicroPython v1.17. When I go to the webpage by entering the IP address of the esp32 then it loads a page with the two buttons. I can click a button and another, say the “on” then the “off” button, then after clicking the second button it gives me the aforementioned error. Any idea what may be doing the error?

Reply

Roger
January 22, 2022 at 3:52 pm
Hi Sara, Rui,

Thanks for this tutorial.
I startet with the LED blink example and could get it running on a ESP32 Devkit C v4.

When I try the webserver control outputs example I get following messages (I did change SSID and password in boot.py to my credentials):
rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:2
load:0x3fff0008,len:8
load:0x3fff0010,len:3408
load:0x40078000,len:9488
load:0x40080000,len:252
entry 0x40080034
[0;32mI (1994) cpu_start: Pro cpu up.[0m
[0;32mI (1994) cpu_start: Single core mode[0m
[0;32mI (1996) heap_alloc_caps: Initializing. RAM available for dynamic allocation:[0m
[0;32mI (2008) heap_alloc_caps: At 3FFAFF10 len 000000F0 (0 KiB): DRAM[0m
[0;32mI (2029) heap_alloc_caps: At 3FFB3000 len 00005000 (20 KiB): DRAM[0m
[0;32mI (2050) heap_alloc_caps: At 3FFBBB28 len 00002000 (8 KiB): DRAM[0m
[0;32mI (2070) heap_alloc_caps: At 3FFE0A18 len 000035E8 (13 KiB): D/IRAM[0m
[0;32mI (2092) heap_alloc_caps: At 3FFE4350 len 0001BCB0 (111 KiB): D/IRAM[0m
[0;32mI (2113) heap_alloc_caps: At 4009457C len 0000BA84 (46 KiB): IRAM[0m
[0;32mI (2134) cpu_start: Pro cpu start user code[0m
[0;32mI (2194) cpu_start: Starting scheduler on PRO CPU.[0m
[0;32mI (2618) modsocket: Initializing[0m
I (2618) wifi: wifi firmware version: 72ddf26
I (2618) wifi: config NVS flash: enabled
I (2618) wifi: config nano formating: disabled
[0;32mI (2618) system_api: Base MAC address is not set, read default base MAC address from BLK0 of EFUSE[0m
[0;32mI (2628) system_api: Base MAC address is not set, read default base MAC address from BLK0 of EFUSE[0m
I (2648) wifi: Init dynamic tx buffer num: 32
I (2648) wifi: Init dynamic rx buffer num: 64
I (2648) wifi: wifi driver task: 3ffb7b70, prio:23, stack:4096
I (2648) wifi: Init static rx buffer num: 10
I (2658) wifi: Init dynamic rx buffer num: 0
I (2658) wifi: Init rx ampdu len mblock:7
I (2668) wifi: Init lldesc rx ampdu entry mblock:4
I (2668) wifi: wifi power manager task: 0x3ffe63ac prio: 21 stack: 2560
I (2678) wifi: wifi timer task: 3ffe7424, prio:22, stack:3584
[0;32mI (2698) phy: phy_version: 355.1, 59464c5, Jun 14 2017, 20:25:06, 0, 0[0m
I (2698) wifi: mode : null
Traceback (most recent call last):
File “boot.py”, line 15, in
AttributeError: ‘module’ object has no attribute ‘osdebug’

line 14 and 15 in boot.py are as follows:
import esp
esp.osdebug(None)

Reply

Roger
January 22, 2022 at 4:17 pm
I commented the line esp.osdebug(None) and it seems to connect.
What is it supposed to do? Provide some methods for debugging?

Best regards,
Roger

Reply

Charles
February 1, 2022 at 6:11 am
This is excellent. Thank you!!

Reply

Marcos
February 26, 2022 at 6:08 pm
hello,
I recommend to use this portion of code right before creation of the socket:
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

or else you will have sometimes the error: “OSError: [Errno 98] EADDRINUSE”

Reply

Sara Santos
February 26, 2022 at 6:37 pm
Thanks for the tip.

Reply

Kumar
March 30, 2022 at 12:54 pm
Hello Sara, I have setup the web server on ESP32 and it works great to turn On/Off onboard LED without any issue at all. But there is one issue I’m facing i.e. after sometime the ESP board hangs-up and doesn’t show the web page when try to send On/Off command again. It doesn’t respond and not connect to board. After resetting the board it works again and open the On/Off web page. I need to have reset the board every time after sometime to make the web page work. How to fix this issue? Thanks.

Reply

Kumar
March 30, 2022 at 2:15 pm
Hello Sara,
I have setup the web server on ESP32 and it works great to turn On/Off onboard LED without any issue at all. But there is one issue I’m facing i.e. after sometime the ESP board hangs-up and doesn’t show the web page when try to send On/Off command again. It doesn’t respond and not connect to board. After resetting the board it works again and open the On/Off web page. I need to have reset the board every time after sometime to make the web page work. How to fix this issue? Thanks.

Reply

João
April 8, 2022 at 6:22 pm
Hello Sara,
Great tutorial, this is the second ESP32 tutorial i follow and it was very detailed. I struggled a bit to find a tutorial like this, that goes step by step and explaining everything. Very good for begginers like me.
In the webserver tutorial everything seems to work fine, i get connection successfull and the details of the connection (browser, device…) however the webpage does not load, what could be causing this issue?
Thank you in advance.
Best regards,
João

Reply

Sara Santos
April 8, 2022 at 8:46 pm
Hi.
What exactly do you get on the web browser window?
Regards,
Sara

Reply

João
April 8, 2022 at 9:51 pm
Hello,
It just keep loading but never actually opens the webpage
Best regards,
João

Reply

João
April 8, 2022 at 10:20 pm
Hello Sara,
I found ou the error i did. It was an identation mistake, making it so that the server’s response would stay out of the loop, never being executed.
Best regards,
João

Reply

Angel
November 9, 2022 at 9:15 am
If I were to replace the button with a slider to control a servo motor what would I need to do to get said value from slider?

Reply

steve cornish
November 9, 2022 at 6:41 pm
Use setInterval() method. e.g.

setInterval(function(){ websocket.send(“X” + String(Joy3.GetX())); }, 100);

In this case I am getting a value from a javascript joystick every 100ms. Note if you make the interval to short and the ESP cannot fully process the request, then it will hang or I should say not do as expected

Reply

VIRAKONE SONETHASACK
January 11, 2023 at 6:21 pm
Hello,

Just wondering how I could add and LED position to the url?

ex. 11.11.111.11/?ledPosition=5&led=on

Would love to be able to turn on a specific LED (one at at time) with a url request and something like below from MicroPython addressable LED page: https://randomnerdtutorials.com/micropython-ws2812b-addressable-rgb-leds-neopixel-esp32-esp8266/

#number of total leds
n = 50

#pin 2
p = 2

#specific Led to light up
ledPosition = 7

np = neopixel.NeoPixel(machine.Pin(p), n)

np[ledPosition] = (255, 0, 0)
np.write()

Reply

VS
January 12, 2023 at 8:55 pm
Just wanted to add that I’m getting a status 500 error:

System.Net.WebException: The server committed a protocol violation. Section=ResponseStatusLine

from the response from the ESP8266, any thoughts?

Reply

Till
May 9, 2023 at 9:26 am
Great tutorial and it works. But I think the line

request = str(request)

is not exactly what you intended. This gives a string of the form b’GET…. (note the leading b’)

You probably intended something like
request = request.decode()
to convert from bytearray to string.

Reply

Michal
June 13, 2023 at 9:27 am
After few minutes i open the website, i get this error: OSError: [Errno 104] ECONNRESET
Please how to solve that issue?

Reply

Mark Maddox
June 28, 2023 at 4:21 pm
Hi Sara,
Great tutorial! Easy to follow and it works well.

Any idea on how to serve images? I’ve uploaded images, and the html debug gives a 200 code, but they don’t display…

Thanks

Reply

Sara Santos
June 28, 2023 at 6:02 pm
How are you serving the images?

Reply

mark maddox
June 28, 2023 at 6:42 pm
I’m using and esp32 with micropython

Reply

Sara Santos
June 29, 2023 at 9:11 am
Where are they hosted? Do you save them in the filesystem?
Are they on a website?
Regards,
Sara

Reply
Leave a Comment
Comment

Name
Name *
Email
Email *
Website
Website
 Notify me of follow-up comments by email.

 Notify me of new posts by email.

Learn MicroPython

MicroPython Introduction

Thonny IDE Install

VS Code Install

Flash Firmware esptool.py

MicroPython Programming

MicroPython GPIOs

ESP32 Pinout

MicroPython Inputs Outputs

MicroPython PWM

MicroPython Analog Inputs

MicroPython Interrupts

ESP32 Deep Sleep

ESP8266 Deep Sleep

Web Servers

MicroPython Output Web Server

MicroPython Relay Web Server

MicroPython DHT Web Server

MicroPython BME280 Web Server

MicroPython BME680 Web Server

MicroPython DS18B20 Web Server

Sensors and Modules

MicroPython Relay Module

MicroPython PIR

MicroPython DHT11/DHT22

MicroPython BME280

MicroPython BME680

MicroPython DS18B20

MicroPython Multiple DS18B20

Weather Station Datalogger

MicroPython OLED

MicroPython OLED Draw Shapes

MicroPython WS2812B LEDs

MicroPython HC-SR04

MQTT

MicroPython MQTT Introduction

MQTT DHT11/DHT22

MQTT BME280

MQTT BME680

MQTT DS18B20

Useful Guides

MicroPython Access Point

MicroPython WiFiManager

uPyCraft IDE Windows

uPyCraft IDE Mac OS X

uPyCraft IDE Linux

Flash MicroPython Firmware

Learn More

Learn ESP32

Learn ESP8266

Learn ESP32-CAM

Learn MicroPython

Learn Arduino

MicroPython eBook »

Search for:
Search …

Learn ESP32 with Arduino IDE (2nd Edition) Course » Complete guide to program the ESP32 with Arduino IDE!


SMART HOME with Raspberry Pi, ESP32, and ESP8266 » learn how to build a complete home automation system.


🔥 Learn Raspberry Pi Pico/Pico W with MicroPython​ » The complete getting started guide to get the most out of the the Raspberry Pi Pico/Pico W (RP2040) microcontroller board using MicroPython programming language.




AboutSupportTerms and ConditionsPrivacy PolicyRefundsComplaints’ BookMakerAdvisor.comJoin the Lab
Copyright © 2013-2024 · RandomNerdTutorials.com · All Rights Reserved
Update Privacy Settings
