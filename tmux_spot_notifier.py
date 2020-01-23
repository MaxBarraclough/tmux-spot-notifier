

## AUTHORS
## This script was written by Max Barraclough

## LICENCE
## This script is released under the ISC Licence, see LICENCE.txt.
## (It does not include the 'loss of mind' clause seen in the tmux
## variation of the licence.)

## INSTALLATION
##
## Runs in Python3 only, *not* Python2.
## Setting up on Ubuntu:
##
## sudo apt-get update && sudo apt-get install python3-pip
## sudo -K
## python3 -m pip install --user libtmux requests ## DO NOT run this under sudo

## BACKGROUND
##
## We don't use the Unix 'wall' command, as that causes fullscreen CLI
## applications (e.g. vim) to misrender until refreshed

## Non-standard libs:
import libtmux
import requests

## Standard libs:
import signal
import functools
import datetime
import threading
import time
import argparse
import sys

## Pointless as you'll probably see a syntax error first, but, for good measure:
if (sys.version_info.major != 3):
    raise Exception("Python 3 is required")


## Doc:     https://aws.amazon.com/blogs/aws/new-ec2-spot-instance-termination-notices/
## Related: https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/instancedata-data-retrieval.html
##          https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/instancedata-dynamic-data-retrieval.html
def block_until_doomed():

    doomed = False

    while not doomed:
        ## Amazon give 2 minutes notice ('notification') before termination of a spot instance.
        ## This fetch gives 404 unless there's impending termination.
        r = requests.get("http://169.254.169.254/latest/meta-data/spot/termination-time")
        sc = r.status_code

        was_404 = (404 == sc)
        doomed = not was_404

        if (not doomed):
            if (not args.quiet_mode):
                print(datetime.datetime.now().isoformat() + "    Instance is not doomed")
            time.sleep(5)

    if (not args.quiet_mode):
        print(datetime.datetime.now().isoformat() +
              "    THIS INSTANCE HAS BEEN NOTIFIED. TERMINATION IN 1m55s") ## Assume worst case
        print("Details: " + r.text)


def display_warning(session, msg):
    ## tmux shows messages for far too little time, so we force the matter:
    t1 = threading.Timer(0.5, session.attached_pane.display_message, [msg])
    t2 = threading.Timer(1.0, session.attached_pane.display_message, [msg])
    t3 = threading.Timer(1.5, session.attached_pane.display_message, [msg])
    t4 = threading.Timer(2.0, session.attached_pane.display_message, [msg])
    t5 = threading.Timer(2.5, session.attached_pane.display_message, [msg])
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    session.attached_pane.display_message(msg)

def ring_bell():
    print("\007", end="", flush=True)

def handle_notification(server, session):
    ## We could inspect the string returned from the request,
    ## but that opens the door to timezone issues / host clock issues.
    ## We check every 5 seconds, so on average we detect the notification 2.5 seconds late.
    ## We will play it safe and assume we got the worst case, running 5 seconds late.

    ring_bell()
    t1_ = threading.Timer(2, ring_bell)
    t2_ = threading.Timer(4, ring_bell)
    t1_.start()
    t2_.start()

    t1 = threading.Timer(            10.0, display_warning, [session, "1 minute 45 seconds until termination"])
    t2 = threading.Timer(      15  + 10.0, display_warning, [session, "1 minute 30 seconds until termination"])
    t3 = threading.Timer( (2 * 15) + 10.0, display_warning, [session, "1 minute 15 seconds until termination"])
    t4 = threading.Timer( (3 * 15) + 10.0, display_warning, [session, "1 minute until termination"])
    t5 = threading.Timer( (4 * 15) + 10.0, display_warning, [session, "45 seconds until termination"])
    t6 = threading.Timer( (5 * 15) + 10.0, display_warning, [session, "30 seconds until termination"])
    t7 = threading.Timer( (6 * 15) + 10.0, display_warning, [session, "15 seconds until termination"])
    t8 = threading.Timer( (6 * 15) + 23.5, display_warning, [session, "Termination imminent"])
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    t6.start()
    t7.start()
    t8.start()


def make_status_bar_red_and_schedule_black(session):
    session.cmd("set", "-g", "status-bg", "red")
    session.cmd("set", "-g", "status-fg", "black")
    t = threading.Timer(1.6, make_status_bar_black_and_schedule_red, [session])
    t.start()

def make_status_bar_black_and_schedule_red(session):
    session.cmd("set", "-g", "status-bg", "black")
    session.cmd("set", "-g", "status-fg", "red")
    t = threading.Timer(1.6, make_status_bar_red_and_schedule_black, [session])
    t.start()


## Omitting the read-only lock would open the door to issues resetting
## the background colour back to black after a 'blink'
def lock_and_blink_panes(server, session, invoke_afterwards):
    session.cmd("switch-client", "-r")
    blink_panes_red_and_schedule_reset(server, session, 0, invoke_afterwards)

def blink_panes_red_and_schedule_reset(server, session, num_previous_blinks, invoke_afterwards):
    session_name = session.get('session_name')
    ps = session.attached_window.panes

    for p in ps: ## Manipulate background of all panes of the current window
        pane_index = p.index
        pane_index_str = str(pane_index)
        pane_str = session_name + "." + pane_index_str ## takes the form of "mysession.0"
        session.cmd("select-pane", "-t", pane_str, "-P", "bg=red")

    session.cmd("set", "-g", "status-bg", "red")
    session.cmd("set", "-g", "status-fg", "black")
    t = threading.Timer(0.9, reset_panes_and_schedule_blink,
                       [server, session, num_previous_blinks + 1, invoke_afterwards])
    t.start()

def reset_panes_and_schedule_blink(server, session, num_previous_blinks, invoke_afterwards):
    session_name = session.get('session_name')
    ps = session.attached_window.panes

    for p in ps:
        pane_index = p.index
        pane_index_str = str(pane_index)
        pane_str = session_name + "." + pane_index_str
        session.cmd("select-pane", "-t", pane_str, "-P", "bg=black")

    session.cmd("set", "-g", "status-bg", "black")
    session.cmd("set", "-g", "status-fg", "red")

    if (num_previous_blinks >= 3):
        session.cmd("switch-client", "-r") ## unset read-only
        invoke_afterwards()
    else:
        t = threading.Timer(0.9, blink_panes_red_and_schedule_reset,
                           [server, session, num_previous_blinks, invoke_afterwards])
        t.start()


def handle_exit_signal(signalNumber, frame):
    exit(0)


def register_exit_handler():
    signal.signal(signal.SIGTERM, handle_exit_signal)
    signal.signal(signal.SIGINT,  handle_exit_signal)


def parse_arguments():
    epi = \
"""   Run this script on an Amazon EC2 spot instance, in its own tmux window (tab),
   ideally window 0 to keep it out of the way.

   If/when your instance gets its termination notification
   (2 minutes before termination occurs), by default this script does this:

     * Ring the bell sound several times (print the bell metacharacter)
     * Blink the status bar red and black until the instance is terminated
     * Every 15 seconds, display a message to the user

   Alternatively, if --enable-fullscreen-blink has been passed:
     * Lock the session into read-only mode
       * The way this works in tmux, the client's focus is forced back
         to the session you specified in the mandatory command-line argument
       * This is annoying if using multiple sessions as this user
     * Cause all tmux panes in the current tmux window to blink red
     * Cause the status bar to blink in time with this, giving a fullscreen blink
     * Continue this fullscreen blinking for a few seconds
     * When done, disable read-only mode
     * Switch over to the usual blinking status bar from here until termination

   Everything the script does is contained to the user under which it is run.
"""

    parser = argparse.ArgumentParser(description='tmux notifier for Amazon EC2 spot-instance termination notifications',
                                     epilog=epi,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    ## Mandatory position argument
    sess_help = 'Name of target tmux session. Other sessions will still see the blinking status-bar, but not the countdown messages.'
    parser.add_argument(dest='target_session_name', type=str, help=sess_help)


    ## Optional arguments

    ## Don't try 'type=bool' https://stackoverflow.com/a/15008806/
    parser.add_argument('-q', '--quiet', dest='quiet_mode', default=False,
                        action='store_true', help='Quiet mode. Suppresses log output.')

    efb_help = 'When spot notification is detected, briefly lock the client'     + \
               ' into read-only mode and run a highly visible fullscreen blink.' + \
               ' Do not use if using multiple tmux sessions as the same user.'

    parser.add_argument('-b', '--enable-fullscreen-blink', dest='enable_fullscreen_blink',
                        default=False, action='store_true', help=efb_help)

    args = parser.parse_args()
    return args


args = parse_arguments()

target_session_name = args.target_session_name

server = libtmux.Server()

existing_sessions       = server.list_sessions()
existing_sessions_names = [ s.get('session_name') for s in existing_sessions ]
existing_sessions_dict  = dict(zip(existing_sessions_names, existing_sessions))

## 'in' looks at the *keys* of the dict
session_name_was_found = (target_session_name in existing_sessions_dict)

if (session_name_was_found):
    target_session = existing_sessions_dict[target_session_name]
    register_exit_handler()
#   time.sleep(4)
    block_until_doomed()

    #######################################################
    ###  Our instance is now doomed. Doomed. DOOOOMED!  ###
    #######################################################

    handle_notification(server, target_session)

    if (args.enable_fullscreen_blink):
        ## Bind then pass nullary function
        invoke_afterwards = functools.partial(make_status_bar_red_and_schedule_black, target_session)
        lock_and_blink_panes(server, target_session, invoke_afterwards)
    else:
        make_status_bar_red_and_schedule_black(target_session)

    ## Don't worry about exiting gracefully, instead, keep 'animating' until the instance goes down.
    time.sleep(180) ## Instance termination will occur long before this sleep expires.

else:
    print("tmux session not found:", "'" + target_session_name + "'", file=sys.stderr)

