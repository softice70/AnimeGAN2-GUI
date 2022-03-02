#! /usr/bin/python
# -*-coding: UTF-8 -*-

import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from cartoon_wnd import CartoonWindow


class MainWindow:
    MIN_SIZE = (1320, 800)

    def __init__(self):
        self._cartoon_wnd = CartoonWindow()
        self._client_size = (MainWindow.MIN_SIZE[0] - 16, MainWindow.MIN_SIZE[1] - 39)
        self._min_client_size = self._client_size

    def run(self):
        dpg.create_context()
        self._init_font_registry()
        self._init_scheme()
        self._init_window()

        dpg.create_viewport(title='animeGan', width=MainWindow.MIN_SIZE[0], height=MainWindow.MIN_SIZE[1], min_width=MainWindow.MIN_SIZE[0], min_height=MainWindow.MIN_SIZE[1])
        dpg.setup_dearpygui()
        # dpg.show_debug()
        # demo.show_demo()
        # dpg.show_style_editor()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        self._set_on_size_handler()
        dpg.start_dearpygui()
        dpg.destroy_context()

    def _init_window(self):
        with dpg.window(tag="primary_window"):
            self._cartoon_wnd.init_window(self._client_size)

    def _set_on_size_handler(self):
        with dpg.item_handler_registry(tag="main_window_handler"):
            dpg.add_item_resize_handler(callback=self._on_size)
        dpg.bind_item_handler_registry("primary_window", "main_window_handler")

    def _on_size(self, sender, app_data, user_data):
        config = dpg.get_item_configuration("primary_window")
        if config["width"] >= self._min_client_size[0] and config["height"] >= self._min_client_size[1] \
                and (config["width"] != self._client_size[0] or config["height"] != self._client_size[1]):
            self._client_size = (config["width"], config["height"])
            self._cartoon_wnd.on_size(self._client_size)

    # 加载字库，设置默认字体显示中文
    @staticmethod
    def _init_font_registry():
        with dpg.font_registry():
            with dpg.font("./resource/OPPOSans-M.ttf", 20) as font_ch:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
                dpg.bind_font(font_ch)

    # 调整默认主题的部分设置
    @staticmethod
    def _init_scheme():
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
        dpg.bind_theme(global_theme)


if __name__ == '__main__':
    main_wnd = MainWindow()
    main_wnd.run()

