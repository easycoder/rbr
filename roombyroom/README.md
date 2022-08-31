# The RBR files

The files in this project are in 2 groups; the Controller and the Server.

Controller files are those that run on a local server in the premises. This is typically a Raspberry Pi running in headless mode. The software is written in a mixture of Python and EasyCoder, the latter being a high-level compiler/runtime itself written in Python. All the source files for this are present. The rationale for using this approach is discussed in the Help files of the user interface, at [https://rbrheating.com](https://rbrheating.com).

Server files are located on an external web server; typically on public shared hosting, but system implementors are free to install them on a private server if they prefer. There is one PHP file; a small REST server which handles all the communication between the user and the controller. The rest of the files are as follows:

  1. User interface descriptors written in "Webson" format, a formal representation of the DOM coded as JSON. A JavaScript engine converts these to DOM structures on the fly. Webson is an EasyCoder project and has its own repository.
  1. Operating scripts written in EasyCoder. This is almost identical to the language running on the system controller, but written in JavaScript rather than Python. Scripts are compiled on the fly and run, avoiding the need for any build toolchain. Again, the rationale is discussed in the Help stack.
  2. Help scripts, written in enhanced Markdown using a customized version of a JavaScript library called Storyteller, which is another project in the EasyCoder family and is available in the repository.

The general principle is that all software development is done with a regular text editor, working on the live site files or copies of them on a development server. No special deployment step is needed; the results of changes are visible instantly.
