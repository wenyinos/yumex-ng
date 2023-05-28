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
# Copyright (C) 2023  Tim Lauridsen

from __future__ import annotations

from typing import Iterable
from yumex.backend.dnf.factory import DnfBackendFactory

from yumex.utils.types import MainWindow
from yumex.backend.cache import YumexPackageCache
from yumex.backend.dnf import YumexPackage
from yumex.backend.flatpak.backend import FlatpakBackend
from yumex.constants import BACKEND
from yumex.backend.interface import (
    BackendFactory,
    PackageBackend,
    PackageCache,
    Progress,
)
from yumex.utils.enums import (
    InfoType,
    PackageBackendType,
    PackageFilter,
    Page,
    SearchField,
)


class YumexPresenter:
    """presenter class in Model-view-presenter (MVP) architectural pattern

    It works as a middle man between the UI and backend package data, so the UI can work
    diffent package backend in a more generic way.

    The used package backends, implement the PackageBackend protocol methods, so the UI has a well
    defined interface to using the backend without knowledge of packaging API used.

    Implements Presenter,PackageBackend,PackageCache protocols
    """

    def __init__(self, win: MainWindow, factory: BackendFactory = None) -> None:
        self._win: MainWindow = win
        self._backend: PackageBackend = None
        self._root_backend: PackageBackend = None
        self._cache: YumexPackageCache = None
        self._fp_backend: FlatpakBackend = None
        if factory is None:
            self.dnf_backend_factory: BackendFactory = DnfBackendFactory(
                PackageBackendType(BACKEND.lower()), presenter=self
            )
        else:
            self.dnf_backend_factory = factory

    @property
    def package_backend(self) -> PackageBackend:
        if not self._backend:
            self._backend: PackageBackend = self.dnf_backend_factory.get_backend()
        return self._backend

    @property
    def package_root_backend(self) -> PackageBackend:
        if not self._root_backend:
            self._root_backend: PackageBackend = (
                self.dnf_backend_factory.get_root_backend()
            )
        return self._root_backend

    @property
    def package_cache(self) -> PackageCache:
        if not self._cache:
            self._cache: PackageCache = YumexPackageCache(backend=self.package_backend)
        return self._cache

    @property
    def flatpak_backend(self):
        if not self._fp_backend:
            self._fp_backend = FlatpakBackend(self._win)
        return self._fp_backend

    @property
    def progress(self) -> Progress:
        return self._win.progress

    def reset_backend(self) -> None:
        del self._backend
        self._backend = None

    def reset_flatpak_backend(self) -> None:
        del self._fp_backend
        self._fp_backend = None

    def reset_cache(self) -> None:
        del self._cache
        self._cache = None

    # PackageBackend implementation
    def search(self, txt: str, field: SearchField, limit: int) -> list[YumexPackage]:
        return self.package_backend.search(txt, field, limit)

    def get_package_info(self, pkg: YumexPackage, attr: InfoType) -> str | None:
        return self.package_backend.get_package_info(pkg, attr)

    def get_repositories(self) -> list[str]:
        return self.package_backend.get_repositories()

    def depsolve(self, pkgs: Iterable[YumexPackage]) -> list[YumexPackage]:
        return self.package_backend.depsolve(pkgs)

    # PackageCache protocol implementation
    def get_packages_by_filter(
        self, pkgfilter: PackageFilter, reset=False
    ) -> list[YumexPackage]:
        return self.package_cache.get_packages_by_filter(pkgfilter, reset)

    def get_packages(self, pkgs: list[YumexPackage]) -> list[YumexPackage]:
        return self.package_cache.get_packages(pkgs)

    def get_package(self, pkg: YumexPackage) -> YumexPackage:
        return self.package_cache.get_package(pkg)

    # Main Window helpers

    def get_main_window(self) -> MainWindow:
        return self._win

    def show_message(self, title, timeout=2):
        self._win.show_message(title, timeout)

    def set_needs_attention(self, page: Page, num: int):
        """set the page needs_attention state"""
        self._win.set_needs_attention(page, num)

    def confirm_flatpak_transaction(self, refs: list) -> bool:
        return self._win.confirm_flatpak_transaction(refs)

    def select_page(self, page: Page):
        self._win.select_page(page)

    def set_window_sesitivity(self, sensitive: bool):
        self._win.set_sesitivity(sensitive)
