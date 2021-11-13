#!/usr/bin/env python3
# Run this file as python

"""
Stream-based video GUI downloader
version: 1.2
powered by streamlink, tkinter,
made by D. H. Kim.

when executed from other module,
use build() to get root class,
and call root class(or build()()) to mainloop.

"""


# Check environment

import sys

if sys.version_info < (3, 6):
    if __name__ != '__main__':
        raise ImportError(
            "Requires python version upper than or equal with 3.6!"
        )
    sys.stderr.write(
        "Requires python version upper than or equal with 3.6!\n"
        "Current version is %s.\n" % sys.version
    )
    sys.stderr.flush()
    sys.exit(0)

try:
    import _tkinter as _
    del _
except ImportError:
    if __name__ != '__main__':
        raise
    sys.stderr.write(
        "your Python may not be configured for Tk!\n"
    )
    sys.stderr.flush()
    sys.exit(0)

try:
    import streamlink as _
    del _
except ModuleNotFoundError:  # if streamlink doesn't installed, install by pip.
    if __name__ != '__main__':
        raise
    sys.stderr.write(
        "Streamlink is not installed. Trying to install by pip...\n\n"
    )
    sys.stderr.flush()
    from pip.__main__ import _main
    _argv = sys.argv[:]
    sys.argv = ['', 'install', 'streamlink']
    _result = _main()
    if _result:
        sys.exit(_result)
    sys.stdout.write(
        "\nSuccessfully installed.\n"
    )
    sys.stdout.flush()
    sys.argv = _argv[:]
    del _main, _result, _argv


# Import

import os
import json
import time
import contextlib as ctl
import collections as col
import functools as ft
import itertools as it
import typing

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkf
import tkinter.messagebox as tkm

from streamlink.session import Streamlink
from streamlink.exceptions import StreamError, NoPluginError, PluginError


# Global constant

CHUNK_SIZE: (int, float) = 8192
MAX_VIDEO: int = 50
ROOT_TITLE: str = "Stream-based video downloader"
ROOT_RESIZABLE: typing.Sequence = (0, 0)
FILETYPES: typing.Sequence = (
    ("Default lecture file", "*.ts"),
    ("All file", "*.*"),
)
INFO_TEXT: str = (
    "Stream-based video downloader GUI version.\n"
    "powered by python streamlink, tkinter,\n"
    "made by D. H. Kim."
)


# Internal function

def _download(
        url: str, filename: str,
        streamlink: Streamlink = None,
        progress_iterator: typing.Callable = None,
) -> (str, None):
    """
    Downloads video with using streamlink module.
    """

    output = stream_fd = None
    keyboard_interrupted = False
    streamlink = streamlink or Streamlink()

    try:
        # Get stream object
        try:
            streams = streamlink.streams(url)
        except NoPluginError:
            return "No plugin can handle URL: {0}".format(url)
        except PluginError as err:
            return str(err)
        if not streams:
            return "No playable streams found on this URL: {0}".format(url)
        stream = None
        for name, stream in streams.items():
            if stream is streams['best'] and (
                    name not in
                    ["best", "worst", "best-unfiltered", "worst-unfiltered"]
            ):
                stream = streams[name]
                break

        # Get pre-buffer data from stream
        try:
            stream_fd = stream.open()
        except StreamError as err:
            return "Could not open stream: {0}".format(err)
        try:
            pre_buffer = stream_fd.read(CHUNK_SIZE)
        except IOError as err:
            stream_fd.close()
            return "Failed to read data from stream: {0}".format(err)
        if not pre_buffer:
            stream_fd.close()
            return "No data returned from stream"

        # Write all data onto output file from stream
        try:
            output = open(filename, "wb")  # write as binary mode
        except (IOError, OSError) as err:
            return "Failed to open output: {0} ({1})".format(filename, err)
        with ctl.closing(output):
            stream_iterator = it.chain(
                [pre_buffer],
                iter(ft.partial(stream_fd.read, CHUNK_SIZE), b"")
            )
            # Timestamp
            if progress_iterator is not None:
                stream_iterator = progress_iterator(
                    stream_iterator,
                    prefix=os.path.basename(filename),
                )
            try:
                for data in stream_iterator:
                    try:
                        output.write(data)
                    except IOError as err:
                        return "Error when writing to output: {0}, exiting".format(err)
            except IOError as err:
                return "Error when reading from stream: {0}, exiting".format(err)
            finally:
                stream_fd.close()

    except KeyboardInterrupt:
        if output:
            output.close()
        keyboard_interrupted = True

    finally:
        if stream_fd:
            try:
                # log.info("Closing currently open stream...")
                stream_fd.close()
            except KeyboardInterrupt:
                keyboard_interrupted = True
        if keyboard_interrupted:
            raise KeyboardInterrupt


def download(iterable: typing.Sequence = None) -> int:
    # for console usage (not used in main program)
    """Download video using information in iterable sequence."""
    from streamlink_cli.utils import progress
    session = Streamlink()
    try:
        for url, filename in iterable:
            result = _download(
                url, filename, streamlink=session, progress_iterator=progress
            )
            if result:
                sys.stderr.write(result)
                sys.stderr.write("\n")
                sys.stderr.flush()
                return 1
        return 0
    except KeyboardInterrupt:
        sys.stderr.write("Interrupted, terminating...")
        sys.stderr.flush()
        return 130


def format_filesize(size: (int, float)) -> str:
    """Formats the file size into a human readable format."""
    for suffix in ("bytes", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            if suffix in ("GB", "TB"):
                return "{0:3.2f} {1}".format(size, suffix)
            else:
                return "{0:3.1f} {1}".format(size, suffix)
        size /= 1024.0
    return "{0:3.2f} {1}".format(size, "PB")


def format_time(elapsed: (int, float)) -> str:
    """Formats elapsed seconds into a human readable format."""
    hours = int(elapsed / (60 * 60))
    minutes = int((elapsed % (60 * 60)) / 60)
    seconds = int(elapsed % 60)
    return (
        ("{0}h ".format(hours) if hours else "") +
        ("{0}m ".format(minutes) if elapsed > 60 else "") +
        ("{0}s".format(seconds))
    )


def _ask_new_file() -> str:
    filename = tkf.asksaveasfilename(
        title="Save video as..",
        filetypes=FILETYPES
    )
    if filename:
        return _check_filename(filename)
    return filename


def _check_filename(filename: str) -> str:
    fn = os.path.split(filename)[1].split('.')
    if len(fn) < 2:
        filename += '.ts'   
    return filename


# Struct

class Base(object):
    """Base"""

    _type = None

    @classmethod
    def get_type(cls):
        if cls._type is None:
            raise NotImplementedError("Type not defined")
        return cls._type


class Root(Base):
    """Root."""

    _type = 0

    def __init__(self, *params):
        self._setup()
        self._registered = {}
        structure = []
        toolset = []
        for cls in params:
            assert issubclass(cls, Base)
            code = cls.get_type()
            if code == 1:
                structure.append(cls)
            elif code == 2:
                toolset.append(cls)
        for cls in structure:
            self.register_structure(cls)
        for cls in toolset:
            self.register_toolset(cls)

    def __call__(self):
        self.root.mainloop()

    def __delattr__(self, item):
        if item == 'root':
            raise AttributeError('Cannot delete root.')
        else:
            super().__delattr__(item)

    def __getattr__(self, item):
        if item == 'root':
            raise AttributeError('Cannot delete root.')
        try:
            return self._registered[item]
        except KeyError:
            return getattr(self.root, item)

    def _setup(self):
        self.root = self.frame = rt = tk.Tk()
        rt.title(ROOT_TITLE)
        rt.resizable(*ROOT_RESIZABLE)

    def register_structure(self, structure):
        assert isinstance(structure, type)
        key = structure.__name__.lower()
        assert key not in self._registered
        st = self._registered[key] = structure(self.root)
        return st

    def register_toolset(self, toolset):
        assert isinstance(toolset, type)
        key = toolset.__name__.upper()
        assert key not in self._registered
        ts = self._registered[key] = toolset(self.root, **self._registered)
        return ts


class Downloader(Base):
    """
    Downloader.
    Initialized only once and called by download request.
    """

    _type = 1
    # method: __init__, __call__,
    #         _setup, init_total, restore_total, update_total, handle_error, close,
    #         make_iterator, format_filesize, format_time
    # tk-related value:
    main = root = _total_pg = _total_text = _file_text = _progress_text = _bt = None
    # user-defined value:
    val_now = val_total = val_time = val_error = 0
    now_exec = None

    def __init__(self, rt):
        self.root = rt
        self.now_exec = False

    def __call__(self, iterable, length=None):
        assert hasattr(iterable, '__iter__')
        if self.now_exec:
            tkm.showerror('Error', 'Already downloading!')
            return 200
        try:
            self.now_exec = True
            # Destroy previous popup
            if self.main:
                self.main.destroy()
            # Initialize values
            self._setup()
            self.init_total(iterable, length)
            session = Streamlink()
            # Download each video
            try:
                for url, filename in iterable:
                    res = _download(
                        url, filename,
                        streamlink=session,
                        progress_iterator=self.make_iterator
                    )
                    self.update_total()
                    if res:
                        self.handle_error(res, filename)
                        break
            except KeyboardInterrupt:
                pass
            # Close
            return self.close()
        finally:
            self.now_exec = False

    def _setup(self, restore=False):

        self.main = main_popup = tk.Toplevel(self.root)
        main_popup.resizable(0, 0)
        main_popup.title(
            "Initializing..." if not restore else "Download - restoring window..."
        )

        lb = tk.Label(main_popup, text="")
        lb.grid(row=0, column=0)

        lb = tk.Label(main_popup, text=" Total:")
        lb.grid(row=1, column=0)
        self._total_pg = pg = ttk.Progressbar(main_popup)
        pg.grid(row=1, column=1, ipadx=60)
        pg.step(0)

        self._total_text = text = tk.StringVar()
        text.set(format("-", "^9"))
        lb = tk.Label(main_popup, textvariable=text)
        lb.grid(row=1, column=2)

        lb = tk.Label(main_popup, text="  File:")
        lb.grid(row=2, column=0)
        self._file_text = text = tk.StringVar()
        text.set("-")
        lb = tk.Label(main_popup, textvariable=text)
        lb.grid(row=2, column=1)
        lb = tk.Label(main_popup, text="")
        lb.grid(row=2, column=2)

        lb = tk.Label(main_popup, text="Status:")
        lb.grid(row=3, column=0)
        self._progress_text = text = tk.StringVar()
        text.set(
            "Initializing..." if not restore else "Restoring window..."
        )
        lb = tk.Label(main_popup, textvariable=text)
        lb.grid(row=3, column=1)
        lb = tk.Label(main_popup, text="")
        lb.grid(row=3, column=2)

        lb = tk.Label(main_popup, text="")
        lb.grid(row=4, column=0)

        self._bt = bt = tk.Button(
            main_popup, text="Terminate", width=15,
            command=self.terminate
        )
        bt.grid(row=5, column=1)

        lb = tk.Label(main_popup, text="")
        lb.grid(row=6, column=0)

        main_popup.update()

    def init_total(self, iterable, length=None):
        self.val_time = self.val_now = self.val_error = 0
        try:
            self.val_total = length or len(iterable)
            self._total_text.set(format("0/{0}".format(self.val_total), "^9"))
        except TypeError:  # for iterable which doesn't have __len__():
            self.val_total = 0

    def update_total(self, restore=False):
        if not restore:
            self.val_now += 1
        if self.val_total:
            if not restore:
                self._total_pg.step(100/self.val_total)
            else:
                self._total_pg.step(100*self.val_now/self.val_total)
            self._total_text.set(format("{0}/{1}".format(self.val_now, self.val_total), "^9"))
        else:
            self._total_text.set(format("{0}".format(self.val_now), "^9"))

    def handle_error(self, error_message, filename=None):
        tkm.showerror(
            "Error: {filename}".format(filename=filename or ""),
            str(error_message)
        )
        self.val_error = 1

    def terminate(self):
        self.val_error = 130

    def close(self):
        self._total_pg.step(99.999)
        code = self.val_error
        if code == 0:
            close_text = 'Downloaded successfully'
        elif code == 1:
            close_text = 'Terminated with error'
        elif code == 130:
            close_text = 'Terminated by user'
        else:
            close_text = 'unknown exit code'
        self._file_text.set(close_text)
        self._progress_text.set('Execution time: {0}'.format(
            format_time(self.val_time)
        ))
        self._bt.destroy()
        bt = tk.Button(self.main, text="Close", width=15, command=self.main.destroy)
        bt.grid(row=5, column=1)
        self.main.update()
        self.val_now = self.val_total = self.val_time = self.val_error = 0
        return code

    def make_iterator(self, iterator, prefix):
        speed_updated = start = now = time.time()
        speed_written = written = 0
        speed_history = col.deque(maxlen=5)

        for data in iterator:
            yield data

            now = time.time()
            elapsed = now - start
            written += len(data)

            speed_elapsed = now - speed_updated
            if speed_elapsed >= 0.5:
                speed_history.appendleft((
                    written - speed_written,
                    speed_updated,
                ))
                speed_updated = now
                speed_written = written

                speed_history_written = sum(h[0] for h in speed_history)
                speed_history_elapsed = now - speed_history[-1][1]
                speed = speed_history_written / speed_history_elapsed
                self._file_text.set(prefix)  # added
                self._progress_text.set(  # edited
                    "Written %s (%s @ %s/s)" % (
                        format_filesize(written),
                        format_time(elapsed),
                        format_filesize(speed),
                    )
                )
                # added
                try:
                    self.main.title("Download - %s" % prefix)
                except tk.TclError:
                    self._setup(restore=True)
                    self.update_total(restore=True)
                    self.terminate()
                if self.val_error == 130:
                    raise KeyboardInterrupt
                self.main.update()
        self.val_time += now - start


class TreeView(Base):
    """DataTree."""

    _type = 1
    # method: __init__, __bool__, __len__, __iter__,
    #         _setup, remove_selected, remove_all, get_selection_iter, get_all_iter,
    #         add,
    # tk-related value:
    root = frame = tree = None

    def __init__(self, rt):
        self.root = rt
        self.frame = table_frame = tk.Frame(rt)
        table_frame.grid(row=0)
        self._setup()

    def _setup(self):
        self.tree = treeview = ttk.Treeview(
            self.frame,
            columns=['url', 'filename'],
            displaycolumns=['url', 'filename'],
            height=12
        )
        treeview.pack(side='left')
        treeview.column("#0", width=100,)
        treeview.heading("#0", text="filename")
        treeview.column("url", width=240, anchor='w')
        treeview.heading("url", text="url")
        treeview.column("filename", width=240, anchor='w')
        treeview.heading("filename", text="directory")
        vsb = ttk.Scrollbar(self.frame, orient="vertical", command=treeview.yview)
        vsb.pack(side='right', fill='y')
        treeview.configure(yscrollcommand=vsb.set)

    def add(self, url, filename):
        if len(self.tree.get_children()) <= MAX_VIDEO:
            abspath = os.path.abspath(filename)
            name = os.path.split(abspath)[1]
            self.tree.insert('', 'end', text=name, values=(url, abspath))
        else:
            tkm.showerror(
                "Error: cannot add video", "You can add video upto {0} videos."
                .format(MAX_VIDEO)
            )

    def remove_selected(self):
        self.tree.delete(*(iid for iid in self.tree.selection()))

    def remove_all(self):
        self.tree.delete(*(iid for iid in self.tree.get_children()))

    def __bool__(self):
        return True if self.tree.get_children() else False

    def __len__(self):
        return self.tree.get_children().__len__()

    def __iter__(self):
        for iid in self.tree.get_children():
            item = self.tree.set(iid)
            yield item['url'], item['filename']

    def get_selected_iter(self):
        for iid in self.tree.selection():
            item = self.tree.set(iid)
            yield item['url'], item['filename']

    def get_all_iter(self):
        return iter(self)


class ButtonFrameMaker(Base):
    """makes button frame"""

    _type = 2
    # tk-related value:
    root = frame = treeview = downloader = url_entry = None

    def __init__(self, rt, **params):
        assert 'treeview' in params and 'downloader' in params
        self.root = rt
        self.treeview = params.get('treeview')
        self.downloader = params.get('downloader')
        self.frame = button_frame = tk.Frame(rt)
        button_frame.grid(row=1)
        self._setup()

    def _setup(self):
        button_frame = self.frame
        w = tk.Label(button_frame, text="")
        w.grid(row=0, column=0, columnspan=4)
        w = tk.Label(button_frame, text="stream URL 입력 : ", width=15)
        w.grid(row=1, column=0)
        self.url_entry = e = tk.Entry(button_frame, width=33)
        e.grid(row=1, column=1, columnspan=2)
        w = tk.Button(
            button_frame, text="동영상 추가", width=15,
            command=self._make_add_func()
        )
        w.grid(row=1, column=3)
        w = tk.Label(button_frame, text="")
        w.grid(row=2, column=0, columnspan=4)
        w = tk.Button(
            button_frame, text="선택 제거", width=15,
            command=self.treeview.remove_selected
        )
        w.grid(row=3, column=0)
        w = tk.Button(
            button_frame, text="전체 제거", width=15,
            command=self.treeview.remove_all
        )
        w.grid(row=3, column=1)
        w = tk.Button(
            button_frame, text="선택 저장", width=15,
            command=self._make_save_selected_func()
        )
        w.grid(row=3, column=2)
        w = tk.Button(
            button_frame, text="전체 저장", width=15,
            command=self._make_save_all_func()
        )
        w.grid(row=3, column=3)
        w = tk.Label(button_frame, text="\n")
        w.grid(row=4, column=0, columnspan=4)

    def _make_add_func(self):

        def command():
            url = self.url_entry.get()
            if not url:
                tkm.showwarning("No URL", "Enter URL first.")
                return
            filename = _ask_new_file()
            if filename:
                self.treeview.add(url=url, filename=filename)
                self.url_entry.delete(0, tk.END)

        return command

    def _make_save_selected_func(self):

        def command():
            length = len(self.treeview.tree.selection())
            if length:
                iterator = self.treeview.get_selected_iter()
                self.downloader(iterator, length)
            else:
                tkm.showwarning("No video", "Select any video!")

        return command

    def _make_save_all_func(self):

        def command():
            length = len(self.treeview)
            if length:
                iterator = self.treeview.get_all_iter()
                self.downloader(iterator, length)
            else:
                tkm.showwarning("No video", "Add any video!")

        return command


class MenuMaker(Base):
    """makes menu"""

    _type = 2
    # tk-related value:
    root = treeview = None

    def __init__(self, rt, **params):
        assert 'treeview' in params
        self.root = rt
        self.treeview = params['treeview']
        self._setup()

    def _setup(self):
        rt = self.root

        def quitter():
            if tkm.askyesno("Exit", "Are you sure want to exit?"):
                rt.destroy()

        menubar = tk.Menu(rt)

        menu_1 = tk.Menu(menubar, tearoff=0)
        menu_1.add_command(
            label='영상 목록 저장',
            command=self._make_save_list_func()
        )
        menu_1.add_command(
            label='영상 목록 불러오기',
            command=self._make_load_list_func()
        )
        menu_1.add_separator()
        menu_1.add_command(
            label='종료',
            command=quitter
        )
        menubar.add_cascade(label='파일', menu=menu_1)

        menu_2 = tk.Menu(menubar, tearoff=0)
        menu_2.add_command(
            label='사용 방법',
            command=lambda: tkm.showinfo('Usage', '준비중')
        )
        menu_2.add_command(
            label='정보',
            command=lambda: tkm.showinfo("Information", INFO_TEXT)
        )
        menubar.add_cascade(label='도움말', menu=menu_2)

        rt.config(menu=menubar)

    def _make_load_list_func(self):

        def ask_new_file_error(filename, error=None):
            if tkm.askyesno(
                    "Error: filename error!",
                    "cannot write file \"{0}\":\n"
                    "{1}\n"
                    "instead, we can save as new file\n"
                    "do you want to continue?".format(
                        filename, error or ''
                    )
            ):
                return _ask_new_file()
            return ''

        def command():
            if self.treeview and not tkm.askyesno(
                    "Warning",
                    "Current file information will be lost!\n"
                    "Do you want to continue?"
            ):
                return
            file = tkf.askopenfile(
                    filetypes=(
                            ("Default list file", "*.json"),
                            ("All file", "*.*")
                    ))
            if not file:
                return
            with file:
                try:
                    data = json.loads(file.read())
                except Exception as e:
                    tkm.showerror("Error: cannot open file!", str(e))
                    return
            for index in range(len(data)):
                item = data[index]
                if len(item) != 2:
                    tkm.showerror(
                        "Error: invalid data!",
                        "Data format is invalid."
                    )
                    return
                filename = item[1]
                if os.path.isfile(filename):
                    if not tkm.askyesno(
                        "Warning",
                        "file already exist: {0}\n"
                        "Do you want to continue?\n"
                        "instead, you can save as new file.".format(filename)
                    ):
                        new_filename = _ask_new_file()
                        if not new_filename:
                            return
                        data[index] = [item[0], new_filename]
                        continue
                else:
                    try:
                        temp_file = open(filename, 'w')
                    except (IOError, OSError) as e:
                        new_filename = os.path.abspath(
                            os.path.split(filename)[1]
                        )
                        if os.path.isfile(new_filename):
                            new_filename = ask_new_file_error(filename, e)
                            if not new_filename:
                                return
                            data[index] = [item[0], new_filename]
                            continue
                        else:
                            try:
                                new_temp_file = open(new_filename, 'w')
                            except (IOError, OSError):
                                new_filename = ask_new_file_error(filename, e)
                                if not new_filename:
                                    return
                                data[index] = [item[0], new_filename]
                                continue
                            else:
                                new_temp_file.close()
                                os.remove(new_filename)
                                if tkm.askyesno(
                                    "Error: filename error!",
                                    "cannot write file \"{0}\"\n"
                                    "you can alternatively save as \"{1}\"\n"
                                    "do you want to continue?\n"
                                    "instead, you can save as new file.".format(
                                        filename, new_filename
                                    )
                                ):
                                    data[index] = [item[0], new_filename]
                                else:
                                    new_filename = _ask_new_file()
                                    if not new_filename:
                                        return
                                    data[index] = [item[0], new_filename]
                                    continue
                    else:
                        temp_file.close()
                        os.remove(filename)
            self.treeview.remove_all()
            for url, filename in data:
                self.treeview.add(url, filename)

        return command

    def _make_save_list_func(self):

        def command():
            filename = tkf.asksaveasfilename(
                title="Save list as..",
                filetypes=(
                    ("Default list file", "*.json"),
                    ("All file", "*.*")
                )
            )
            if filename:
                fn = os.path.split(filename)[1].split('.')
                if len(fn) < 2 or fn[-1] != 'json':
                    filename += '.json'
                with open(filename, 'w') as file:
                    file.write(json.dumps(list(map(
                        lambda obj: (obj[0], '/'.join(obj[1].split('\\'))),
                        self.treeview)  # update filename for linux format
                    )))

        return command


# Main program

def build() -> Root:
    return Root(Downloader, TreeView, ButtonFrameMaker, MenuMaker)


if __name__ == '__main__':
    build()()

