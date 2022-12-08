# Protected Message/File Transport Protocol specification
![Version 0.0.1](https://img.shields.io/badge/version-0.0.1-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Illia Chabn](https://img.shields.io/badge/Author-Illia%20Chaban-blue.svg?style=flat)](mailto:xchaban@stuba.sk)
[![ICIT](https://img.shields.io/badge/Github-ICIT-green.svg?style=flat)](https://github.com/ic-it/)



## Contents
- [Introduction](#introduction)
- [Header structure](#header-structure)
    - [Seq number](#seq-number)
    - [Ack number](#sck-number)
    - [flags](#Flags)
        - [SYN](#syn)
        - [ACK](#ack)
        - [UNACK](#unack)
        - [FIN](#fin)
        - [SEND](#send)
        - [PART](#part)
        - [MSG](#msg)
        - [FILE](#file)
    - [Transfer id](#transfer-id)
    - [Checksum](#checksum)
    - [Timeout](#timeout)
- [Data structure](#data-structure)
    - [syn](#syn-ds)
    - [syn-ack](#syn-ack)
    - [syn-send](#syn-send)
        - [syn-send-msg](#syn-send-msg)
        - [syn-send-file](#syn-send-file)
    - [send-part](#send-part)
- [Protocol features](#protocol-features)
    - [Program hierarchy](#program-hierarchy)
    - [Encryption](#encryption)
    - [Binary transfer](#binary-transfer)
    - [Error emulation](#error-emulation)
- [Test client](#test-client)
- [License](#license)

## Introduction
This document describes the specification of the Protected Message/File Transport Protocol (PMFTP). The protocol is designed to provide a secure and reliable transport of messages and files between two hosts. The protocol is based on UDP protocol. The protocol is designed by [Illia Chaban](https://github.com/ic-it).  
Used simple checksum algorithm is based on [RFC1071](https://tools.ietf.org/html/rfc1071). 
Used encryption algorithm is based on [AES](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard).  

## Header structure
The header of the packet is 21 bytes long. The header is divided into 6 fields. The fields are described below.

### Seq number
Individual packet number 

### Ack number
Acknowledgment number

### Flags
The flags field is 1 byte long. The flags field is divided into 8 bits. The bits are described below.
- #### SYN
    SYN flag is used to initiate a connection. The SYN flag is set to 1 when the SYN packet is sent. The SYN flag is set to 0 when the SYN-ACK packet is sent.  
    And using for the first packet of the file transfer.

- #### ACK
    ACK flag is used to acknowledge the receipt of a packet. 
    And using for aknowledge the receipt of the parts of the data transfer.

- #### UNACK
    UNACK flag is used to acknowledge the receipt of a packet.

- #### FIN
    FIN flag is used to terminate a connection.  
    And using for the last packet of the file transfer.

- #### SEND
    SEND flag is used to send a message.

- #### PART
    PART flag is used to send a part of the file.

- #### MSG
    MSG flag is used to send a message.

- #### FILE
    FILE flag is used to send a file.

### Transfer id
Transfer id. Used to identify the transfer.

### Checksum
Checksum is used to verify the integrity of the packet. The checksum is calculated from the header and the data. The checksum is calculated using the [RFC1071](https://tools.ietf.org/html/rfc1071) algorithm.

### Timeout
Timeout is used to set the timeout for the packet. The timeout is set in milliseconds.

## Data structure
The data structure is divided into 4 parts. The parts are described below.

### syn (ds)
The SYN packet is used to initiate a connection. The SYN packet contains publick key in data.

### syn-ack
The SYN-ACK packet is used to acknowledge the receipt of a SYN packet. The SYN-ACK packet contains publick key in data.

### syn-send
The SYN-SEND packet is used to send a message or a file. 

- #### syn-send-msg
    The SYN-SEND-MSG packet is used to send a message. The SYN-SEND-MSG packet contains the message length in the data.

- #### syn-send-file
    The SYN-SEND-FILE packet is used to send a file. The SYN-SEND-FILE packet contains the file length and file name in the data.

### send-part
The SEND-PART packet is used to send a part of the file. The SEND-PART packet contains the part of the file and position in the stram in the data.

## Protocol features

### Program hierarchy
The program is divided into 3 parts.  
Implementation — is a complex system for distributing packets between the layers.  
The first layer is Socket, it creates connections. If a packet belongs to a connection, it passes it to the desired connection.  
The connection in turn distributes the packets within itself, leaving the necessary ones in itself and the rest to the transfers.  

Each level has its own iterator, which is run in priority by the socket. Each iterator has three states: Busy, Sleep and Finish.  
Busy: more iterations are required  
Sleep: pass the time to another iterator  
Finish: end iterator.  
The maximum number of iterations of one iterator in a given iteration of the loop = 40  

This architecture does not require threads for new connections.

![diagram](./diagram.svg)

### Encryption
Header is not encrypted. This is done to save resources and seriously, there is nothing important in the header `\_(._.)_/`.

### Binary transfer
You can transmit data in both directions simultaneously.

### Error emulation
It is possible to intentionally break a random package. But it will just be ignored on the socket side and that's it.

## Test client
The test client is a simple client for testing the protocol. The test client knows how to connect to various other clients, transfer files and messages. 

## License
This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.