# rotiller

Rotiller is a terminal UI for a Chia Full Node.

The goal is to provide a quick and keyboard-only way to inspect the blockchain, wallets, and harvester directly from the terminal.  
It uses **ncurses** for rendering and **Chia RPC** to communicate with the node.

## Status

Garbage in → garbage out.  
This code is alpha. Like… *pre-alpha*. A **very deep pre-alpha**.

Currently, only the **block explorer** is working. There is some code for wallet interaction, but it is **disabled** in this version.

<img width="2977" height="1698" alt="Screenshot from 2026-01-02 22-27-27" src="https://github.com/user-attachments/assets/168d6b2a-c877-4995-ad3a-f8e285afd9e3" />

## Composting Map 🌱

- Puzzle / address viewer  
- Monitor address activity  
- Long term: wallet support, mempool viewer, more block explorer features, Splash network support, and why not trading from the terminal

## Known Issues

- On high-resolution displays with `xterm`, input can become laggy *(increase character size or reduce window size)*
- `tmux`: does not work (color support issues of the python port)
- `zellij`: incorrect color support
- Never tested on MAC and Windows
  
## Installation

### Requirements

- Chia must be installed  
  Tested with **Chia 2.5.7** and **2.5.4**  
  Other versions may have missing dependencies

- Python Dependencies

```
bash
pip install requests
```

- ncurses
```
Ubuntu:
sudo apt-get install libncurses5-dev libncursesw5-dev
```
- copy/paste in linux
```
sudo apt install xclip
```

## Usage

Make rototiller executable:
```
chmod +x rototiller
```

Run it:
```
./rototiller
or
python rototiller
```
