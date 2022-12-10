# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Copyright (C) 2022  Tim Lauridsen
#
#
import re

from gi.repository import Gtk, Adw, Gio, GLib

from yumex.constants import rootdir, app_id, PACKAGE_COLUMNS
from yumex.ui.pachage_view import YumexPackageView
from yumex.ui.queue_view import YumexQueueView
from yumex.utils import log


@Gtk.Template(resource_path=f"{rootdir}/ui/window.ui")
class YumexMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "YumexMainWindow"

    content_packages = Gtk.Template.Child()
    clamp_packages = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    main_view = Gtk.Template.Child()
    content_groups = Gtk.Template.Child()
    content_queue = Gtk.Template.Child()
    main_menu = Gtk.Template.Child("main-menu")
    sidebar = Gtk.Template.Child()
    package_filter = Gtk.Template.Child()
    filter_available = Gtk.Template.Child()
    filter_installed = Gtk.Template.Child()
    filter_updates = Gtk.Template.Child()
    stack = Gtk.Template.Child("view_stack")
    search_button = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    sidebar_button = Gtk.Template.Child("sidebar-button")
    package_paned = Gtk.Template.Child()
    package_info = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = kwargs["application"]
        self.settings = Gio.Settings(app_id)
        self.current_pkg_filer = None
        self.previuos_pkg_filer = None
        # save settings on windows close
        self.connect("unrealize", self.save_window_props)
        # connect to changes on Adw.ViewStack
        self.stack.get_pages().connect("selection-changed", self.on_stack_changed)
        self.setup_gui()
        self.create_action("select_all", self.on_selectall_activate)
        self.create_action("deselect_all", self.on_deselectall_activate)

    def save_window_props(self, *args):
        win_size = self.get_default_size()

        # Save windows size
        self.settings.set_int("window-width", win_size.width)
        self.settings.set_int("window-height", win_size.height)

        # Save coloumn widths
        for setting in PACKAGE_COLUMNS:
            width = getattr(self.package_view, f"{setting}s").get_fixed_width()
            width = self.settings.set_int(f"col-{setting}-width", width)

        self.settings.set_boolean("window-maximized", self.is_maximized())
        self.settings.set_boolean("window-fullscreen", self.is_fullscreen())
        self.settings.set_int("pkg-paned-pos", self.package_paned.get_position())

    def setup_gui(self):
        self.setup_package_page()
        self.setup_groups_page()
        self.setup_queue()

    def setup_package_page(self):
        """Setup the packages page"""
        self.package_view = YumexPackageView(self)
        self.content_packages.set_child(self.package_view)
        # set columns width from settings and calc clamp width
        clamp_width = 100
        for setting in PACKAGE_COLUMNS:
            width = self.settings.get_int(f"col-{setting}-width")
            getattr(self.package_view, f"{setting}s").set_fixed_width(width)
            clamp_width += width
        self.clamp_packages.set_maximum_size(clamp_width)
        self.clamp_packages.set_tightening_threshold(clamp_width)
        self.package_paned.set_position(self.settings.get_int("pkg-paned-pos"))

    def setup_groups_page(self):
        """Setup the groups page"""
        self.content_groups.append(self.create_label_center("Groups"))

    def setup_queue(self):
        """Setup the groups page"""
        self.queue_view = YumexQueueView(self)
        self.content_queue.set_child(self.queue_view)

    def show_message(self, title, timeout=1):
        toast = Adw.Toast(title=title)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
        return toast

    def load_packages(self, pkg_filter: str):
        """Trigger the activation of a given pkg filter"""
        GLib.idle_add(self._load_packages, pkg_filter)

    def _load_packages(self, pkg_filter: str):
        """Helper for Trigger the activation of a given pkg filter
        Using GLib.idle_add
        """
        if pkg_filter in ["updates", "installed", "available"]:
            getattr(self, f"filter_{pkg_filter}").activate()
            self.search_bar.set_search_mode(False)
        return False

    def create_label_center(self, label):

        lbl = Gtk.Label()
        lbl.props.hexpand = True
        lbl.props.vexpand = True
        lbl.props.label = label
        lbl.add_css_class("page_label")
        lbl.add_css_class("accent")
        return lbl

    @Gtk.Template.Callback()
    def on_apply_actions_clicked(self, *_args):
        self.show_message("Apply pressed")

    @Gtk.Template.Callback()
    def on_search_changed(self, widget):
        search_txt = widget.get_text()
        log(f"search changed : {search_txt}")
        if search_txt == "":
            if self.current_pkg_filer == "search":
                # self.last_pkg_filer.activate()
                self.load_packages(self.previuos_pkg_filer)
        elif search_txt[0] != ".":
            # remove selection in package filter (sidebar)
            self.package_filter.unselect_all()
            self.package_view.search(search_txt)
            self.current_pkg_filer = "search"

    @Gtk.Template.Callback()
    def on_search_activate(self, widget):
        allowed_field_map = {
            "name": "name",
            "arch": "arch",
            "repo": "reponame",
            "desc": "summary",
        }
        search_txt = widget.get_text()
        log(f"search activate : {search_txt}")
        if search_txt[0] == ".":
            # syntax: .<field>=<value>
            cmds = re.compile(r"^\.(.*)=(.*)")
            res = cmds.match(search_txt)
            if len(res.groups()) == 2:
                field, key = res.groups()
                if field in allowed_field_map:
                    field = allowed_field_map[field]
                    self.package_filter.unselect_all()
                    log(f"searching for : {key} in pkg.{field}")
                    self.package_view.search(key, field=field)

        else:
            # remove selection in package filter (sidebar)
            self.package_filter.unselect_all()
            self.package_view.search(search_txt)
        self.current_pkg_filer = "search"

    @Gtk.Template.Callback()
    def on_package_filter_activated(self, widget, item):
        entry = self.search_bar.get_child()
        entry.set_text("")
        pkg_filter = item.get_name()
        match pkg_filter:
            case "available":
                self.package_view.get_packages("available")
            case "installed":
                self.package_view.get_packages("installed")
            case "updates":
                self.package_view.get_packages("updates")
        self.current_pkg_filer = pkg_filter
        self.previuos_pkg_filer = pkg_filter
        self.sidebar.set_reveal_flap(False)
        # self.show_message(f"package filter : {item.get_name()} selected")

    def on_selectall_activate(self, *_args):
        # select all work only on updates pkg_filter
        if self.current_pkg_filer in ["updates", "search"]:
            self.package_view.select_all(True)

    def on_deselectall_activate(self, *_args):
        self.package_view.select_all(False)

    def show_on_packages_page(self, show=False):
        """show/hide widget only used on packages page"""
        self.search_button.set_visible(show)
        self.search_bar.set_visible(show)
        self.sidebar_button.set_visible(show)

    def on_stack_changed(self, widget, position, n_items):
        """Called when the stack page is changed"""
        active_name = self.stack.get_visible_child_name()
        log(f"stack changed : {active_name}")
        match active_name:
            case "packages":
                self.show_on_packages_page(show=True)
                self.package_view.refresh()
            case "groups":
                self.show_on_packages_page(show=False)
            case "queue":
                self.show_on_packages_page(show=False)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
            activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
