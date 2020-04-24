
"""
# Adapted from: 
## http://archive.ambermd.org/200511/0085.html

From: David E. Konerding <dekonerding.lbl.gov>
Date: Tue, 08 Nov 2005 15:01:13 -0800

I've written a script that automates the process of rendering movie
frames; I use this script in conjuction with a cluster of compute
nodes that have fast OpenGL cards to remotely render very long movies.
The script basically loads individual trajectory frames,
renders them attractively, and saves the rendered images to files which
can then be assembled using standard movie-making programs.

Run the script something like this:
    > HOSTNAME=pabst.lbl.gov DISPLAY=:1 START=0 STOP=5 WIDTH=640 HEIGHT=480
    > PRMTOP=~/src/topoI/INPUT/topoI.top TRAJECTORY=x.traj
    > MOVIE_BASE=movie_scratch ~/sw/chimera/chimera-1.2172/bin/chimera
    > scripts/movie.py
"""

import tkinter as tk
import chimera, Midas, Trajectory, gzip
from Trajectory.formats.Amber.Amber import Amber
import os, sys, time, traceback, string

from chimera.printer import saveImage

from chimera import dialogs


class MovieCallbacks:
    def __init__(self, f, reply_dialog):
        self.f = f
        self.reply_dialog = reply_dialog
   
    def init_callback(self, start, stop):
        self.start = start
        self.stop = stop
        dialogs.display(tkgui._ReplyDialog.name)

    def size_callback(self):
        if self.reply_dialog:
            x = "-1-1"
        d = dialogs.find(tkgui._ReplyDialog.name)
        d.uiMaster().winfo_toplevel().wm_geometry(x)

    def render_callback(self, frame):
        pass

class MDMovieCallbacks(MovieCallbacks):
    def __init__(self, f, reply_dialog, prmtop, trajectory):
        MovieCallbacks.__init__(self, f, reply_dialog)
        self.prmtop = prmtop
        self.trajectory = trajectory

        self.bondColor = chimera.MaterialColor()
        self.bondColor.ambientDiffuse = (0.0, 0.8, 0.9)
        self.bondColor.opacity = 1

    def init_callback(self, start, stop):
        MovieCallbacks.init_callback(self, start, stop)
       
        self.ensemble = Amber(self.prmtop, self.trajectory, None, None)

        self.frames_done = 0

        if self.start > len(self.ensemble) or self.stop > len(self.ensemble):
            raise RuntimeError("Cannot set start (%d) or stop (%d) greater than length of ensemble (%d)" % (self.start, self.stop, len(self.ensemble)))
        if self.start < 0 or self.stop < 0 or self.start >= stop:
            raise RuntimeError("Cannot set start (%d) or stop (%d) to less than 0 or start greater than or equil to stop" % (self.start, self.stop))

        self.frames_total = self.stop - self.start

        self.molecule = Trajectory.Ensemble(self.ensemble)
        self.molecule.CreateMolecule()
        self.molecule.LoadFrame(1)
        self.molecule.AddMolecule()

        self.refmolecule = Trajectory.Ensemble(self.ensemble)
        self.refmolecule.CreateMolecule()
        self.refmolecule.LoadFrame(1)
        self.refmolecule.AddMolecule()

        Midas.turn("x", -25)
        Midas.turn("z", 25)
        Midas.turn("y", 40)
        Midas.undisplay("#1")
        Midas.ribbon("#0")
        Midas.undisplay("#0")
        Midas.ribcolor("red", "#0:/isHelix")
        Midas.ribcolor("blue", "#0:/isSheet")
        Midas.window("#1")
        Midas.scale(2)

        Midas.wait(1)
        self.t0 = time.time()

    def size_callback(self):
        MovieCallbacks.size_callback(self)
        x = "%dx%d+0+0" % (width+8, height+78)
        chimera.tkgui.app.winfo_toplevel().wm_geometry(x)


    def render_callback(self, frame):
        try:
            self.molecule.deleteCoordSet(self.molecule.coordSets[frame])
        except:
            pass
        self.molecule.LoadFrame(frame+1)
        Midas.match("#0:1-545", "#1:1-545")
        Midas.undisplay("#0")

        Midas.color("byatom", "#0")
        Midas.undisplay("#0.=H=")
        Midas.wait(1)
        t = time.time()

        pct_complete = self.frames_done/float(self.frames_total)*100
        if self.frames_done:
            time_to_complete = (t-self.t0)/self.frames_done * (self.frames_total-self.frames_done)
        else:
            time_to_complete = 0


        self.f.write("Rendered frame %d (%d of %d, %d-%d), %5.2f%% complete, %5.2f seconds remaining)\n" % (frame, self.frames_done, self.frames_total, start, stop, pct_complete, time_to_complete))
        self.f.flush()
        self.frames_done += 1
        return True


class Movie:
    def __init__(self, f, callbacks, movie_base, start, stop):
        self.f = f
        self.callbacks = callbacks
        self.movie_base = movie_base
        self.start = start
        self.stop = stop

    def init(self):
        self.callbacks.init_callback(self.start, self.stop)

    def size(self):
        self.callbacks.size_callback()

    def run(self):
        for i in range(self.start, self.stop):
            path = os.path.join(self.movie_base, "image.%06d.jpg" % i)
            if not os.path.exists(path):
                self.f.write("rendering frame: %d\n" % i)
                self.f.flush()
                self.callbacks.render_callback(i)
                self.snapphoto(path)
            else:
                self.f.write("not rendering frame: %d\n" % i)

           
    def snapphoto(self, path):
        Midas.wait(1)
        saveImage(path, width, height, format="PNG")
        self.f.flush()


if __name__ == '__main__':
    f = open("chimera.%s" % os.getenv('HOSTNAME'), "w")
    #f = sys.stdout
    ## start = int(sys.argv[1])
    ## stop = int(sys.argv[2])
    ## start = 0
    ## stop = 1
    host = os.getenv("HOSTNAME")
    display = os.getenv("DISPLAY")
    start = os.getenv("START")
    stop = os.getenv("STOP")
    width = os.getenv("WIDTH")
    height = os.getenv("HEIGHT")
    prmtop = os.getenv("PRMTOP")
    trajectory = os.getenv("TRAJECTORY")
    movie_base = os.getenv("MOVIE_BASE")

    f.write("%s\n" % str((host, display, start, stop, width, height, prmtop,
    trajectory, movie_base)))

    if not host or not display or not start or not stop or not height or not width or not prmtop or not trajectory or not movie_base: 
        f.write("Error: environment variables not defined\n") 
        f.write("%s\n" % map(lambda x: (x, os.getenv(x)), ['HOSTNAME', "DISPLAY", "START", "STOP", "WIDTH", "HEIGHT", "PRMTOP", "TRAJECTORY", "MOVIE_BASE"]))
        sys.exit(1)

    start, stop, width, height = map(int, (start, stop, width, height))

    f.write("Doing job on %s, display: %s, start: %d, stop: %d, movie_base: %s\n" % (host, display, start, stop, movie_base))
    f.flush()

    try:
        md = MDMovieCallbacks(f, 1, prmtop, trajectory)
        m = Movie(f, md, movie_base, start, stop)
        m.init()
        m.size()
        m.run()
    except:
        error_status = sys.exc_info()
        map(f.write, traceback.format_exception(error_status[0], error_status[1], error_status[2]))
        f.flush()
        sys.exit(1)
    sys.exit(0)