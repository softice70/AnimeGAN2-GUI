#! /usr/bin/python
# -*-coding: UTF-8 -*-

import dearpygui.dearpygui as dpg
import os
from PIL import Image

import torch
from torchvision.transforms.functional import to_tensor, to_pil_image
from model import Generator

torch.backends.cudnn.enabled = False
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


class CartoonWindow:
    def __init__(self):
        self._weight_names = ("celeba", "face paint v1", "face paint v2", "paprika")
        self._weights = {"celeba": "resource/celeba_distill.pt",
                        "face paint v1": "resource/face_paint_512_v1.pt",
                        "face paint v2": "resource/face_paint_512_v2.pt",
                        "paprika": "resource/paprika.pt"}
        self._models = {}
        self._output_dir = 'results'
        self._src_img_id = None
        self._result_img_id = None
        self._client_size = (1280, 640)
        self._img_size = (640, 640)

    def init_window(self, client_size):
        self._set_client_size(client_size)
        # 创建纹理库
        dpg.add_texture_registry(tag="texture_registry_id", show=False)
        # 文件对话框
        with dpg.file_dialog(directory_selector=False, show=False, callback=self._callback,
                             id="file_dialog_id"):
            dpg.add_file_extension("Image files (*.bmp *.jpg *.jpeg *.png *.tiff){.bmp,.jpg,.jpeg,.png,.tiff}",
                                   color=(0, 255, 255, 255))
            dpg.add_file_extension("", color=(150, 255, 150, 255))
            dpg.add_file_extension(".*")

        # 提示信息对话框
        with dpg.window(label="信息", width=300, height=120, modal=True, show=False, pos=(500, 400),
                        horizontal_scrollbar=False, tag="msg_box_id"):
            dpg.add_text(label="", tag="msg_text_id")
            dpg.add_button(label="Close", pos=(230, 80), callback=lambda: dpg.configure_item("msg_box_id", show=False))

        # 工具条
        with dpg.group(horizontal=True, horizontal_spacing=10):
            dpg.add_text("原图片:")
            dpg.add_input_text(hint="请输入原图片文件的路径", width=775, tag="image_path_id",
                               callback=self._callback, on_enter=True)
            dpg.add_button(label="...", callback=lambda: dpg.show_item("file_dialog_id"))
            dpg.add_text("  模型:")
            dpg.add_combo(self._weight_names, width=200, default_value="face paint v2", callback=self._callback,
                          tag="weight_name_id")
            dpg.add_text("  尺寸:")
            dpg.add_combo(("大", "中", "小"), width=50, default_value="大", callback=self._callback,
                          tag="size_name_id")
            dpg.add_button(label="生成", callback=lambda: self._generate())

        # 图片显示区
        with dpg.group(horizontal=True, horizontal_spacing=0, indent=0):
            with dpg.group(width=self._client_size[0]/2, indent=0, tag="src_group_id"):
                dpg.add_text("原图:")
                with dpg.drawlist(width=self._img_size[0], height=self._img_size[1], tag="src_draw_list_id"):
                    self._draw_border()
            with dpg.group(width=self._client_size[0]/2, indent=0, tag="result_group_id"):
                dpg.add_text("卡通图:")
                dpg.add_loading_indicator(pos=(self._client_size[0]*3/4-40, self._client_size[1]/2-20), radius=5.0, show=False, tag="loading_id")
                with dpg.drawlist(width=self._img_size[0], height=self._img_size[1], tag="result_draw_list_id"):
                    self._draw_border(False)

        self._init_model()

    # 加载AnimeGAN训练好的模型文件
    def _init_model(self):
        for key in self._weights.keys():
            device = 'cpu'
            model_path = self._weights[key]
            net = Generator()
            net.load_state_dict(torch.load(model_path, map_location="cpu"))
            net.to(device).eval()
            print(f"model loaded: {key}")
            self._models[key] = net
            
    def _set_client_size(self, client_size):
        print(client_size)
        self._client_size = client_size
        self._img_size = (int((client_size[0] - 30) / 2), client_size[1] - 60 - 16)

    # 显示提示信息
    @staticmethod
    def _show_message(title, text):
        dpg.set_value("msg_text_id", text)
        dpg.configure_item("msg_box_id", label=title)
        dpg.configure_item("msg_box_id", show=True)

    # 显示或隐藏Loading Indicator
    @staticmethod
    def _show_loading(show):
        dpg.configure_item("loading_id", show=show)

    # 回调函数
    def _callback(self, sender, app_data, user_data):
        print("Sender: ", sender)
        print("App Data: ", app_data)
        if sender == "file_dialog_id":
            dpg.set_value("image_path_id", app_data["file_path_name"])
            self._show_image(app_data["file_path_name"])
        elif sender == "image_path_id":
            self._show_image(app_data)

    def on_size(self, client_size):
        self._clear_canvas(True)
        self._clear_canvas(False)
        self._set_client_size(client_size)
        dpg.configure_item("src_group_id", width=self._client_size[0]/2)
        dpg.configure_item("result_group_id", width=self._client_size[0]/2)
        dpg.configure_item("src_draw_list_id", width=self._img_size[0], height=self._img_size[1])
        dpg.configure_item("result_draw_list_id", width=self._img_size[0], height=self._img_size[1])
        dpg.configure_item("loading_id", pos=(self._client_size[0] * 3 / 4 - 40, self._client_size[1] / 2 - 20))
        self._draw_image(True)
        self._draw_image(False)

    # 生成卡通图片
    def _generate(self):
        image_path = dpg.get_value("image_path_id")
        if image_path is not None and image_path != "" and os.path.exists(image_path) \
                    and os.path.splitext(image_path)[-1].lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            self._show_canvas(False, False)
            self._show_loading(True)
            model_name = dpg.get_value('weight_name_id')
            size_name = dpg.get_value('size_name_id')
            width = 1000 if size_name == '大' else 800 if size_name == '中' else 600
            cartoon_image_path = self._generate_cartoon(image_path, model_name, width)
            self._show_image(cartoon_image_path, is_source=False)
            self._show_loading(False)
            self._show_canvas(False, True)
        else:
            self._show_message("错误信息", "请选择有效的图像文件!")

    # 画出边框
    def _draw_border(self, is_source=True):
        draw_list_id = "src_draw_list_id" if is_source else "result_draw_list_id"
        dpg.draw_rectangle((0, 0), (self._img_size[0], self._img_size[1]), color=(100, 100, 100, 255),
                           parent=draw_list_id, thickness=1)
        dpg.draw_rectangle((1, 1), (self._img_size[0] - 2, self._img_size[1] - 2), fill=(25, 25, 25, 255),
                           parent=draw_list_id)

    # 清除图像
    def _clear_canvas(self, is_source=True):
        draw_list_id = "src_draw_list_id" if is_source else "result_draw_list_id"
        theme_cfg = dpg.get_item_theme("primary_window")
        print(theme_cfg)
        dpg.draw_rectangle((0, 0), (self._img_size[0], self._img_size[1]), fill=(37, 37, 38, 255), parent=draw_list_id)

    # 显示或隐藏图像
    @staticmethod
    def _show_canvas(is_source, show=True):
        draw_list_id = "src_draw_list_id" if is_source else "result_draw_list_id"
        dpg.configure_item(draw_list_id, show=show)

    # 画图
    def _show_image(self, img_file, is_source=True):
        if self._load_texture(img_file, is_source):
            self._draw_image(is_source)
        else:
            self._show_message("错误信息", "请选择有效的图像文件!")

    # 画图
    def _draw_image(self, is_source):
        # 清除原图
        self._draw_border(is_source)
        # 画图
        img_id = self._src_img_id if is_source else self._result_img_id
        if img_id is not None:
            width = dpg.get_item_width(img_id)
            height = dpg.get_item_height(img_id)
            d_width = width if width <= self._img_size[0] - 2 else self._img_size[0] - 2
            d_height = int(1.0 * d_width * height / width)
            d_height = d_height if d_height <= self._img_size[1] - 2 else self._img_size[1] - 2
            d_width = int(1.0 * d_height * width / height)
            pmin = (int((self._img_size[0] - d_width) / 2), int((self._img_size[1] - d_height) / 2))
            pmax = (pmin[0] + d_width, pmin[1] + d_height)
            draw_list_id = "src_draw_list_id" if is_source else "result_draw_list_id"
            dpg.draw_image(img_id, pmin, pmax, uv_min=(0, 0), uv_max=(1.0, 1.0), parent=draw_list_id)

    # 画图
    def _load_texture(self, img_file, is_source=True):
        if img_file is not None and img_file != "" and os.path.exists(img_file) \
                    and os.path.splitext(img_file)[-1].lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            # 加载图片
            width, height, channels, data = dpg.load_image(img_file)
            # 删除纹理库中原先的纹理
            img_id = self._src_img_id if is_source else self._result_img_id
            if img_id is not None:
                dpg.delete_item(img_id)
            # 添加新的纹理
            img_id = dpg.add_static_texture(width, height, data, parent="texture_registry_id")
            if is_source:
                self._src_img_id = img_id
            else:
                self._result_img_id = img_id
            return True
        else:
            return False

    # 为AnimeGAN模型加载并处理图像
    @staticmethod
    def _load_image(image_path, width, x32=False):
        def to_32s(x):
            return 256 if x < 256 else x - x % 32

        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        new_w = width
        new_h = int(1.0 * new_w * h / w)
        new_w = to_32s(new_w) if x32 else new_w
        new_h = to_32s(new_h) if x32 else new_h
        img = img.resize((new_w, new_h))
        return img

    # 调用AnimeGAN生成卡通图片
    def _generate_cartoon(self, image_path, model_name, width):
        device = 'cpu'
        upsample_align = False
        net = self._models[model_name]
        os.makedirs(self._output_dir, exist_ok=True)

        image = self._load_image(image_path, width)
        with torch.no_grad():
            image = to_tensor(image).unsqueeze(0) * 2 - 1
            out = net(image.to(device), upsample_align).cpu()
            out = out.squeeze(0).clip(-1, 1) * 0.5 + 0.5
            out = to_pil_image(out)

        save_image_path = os.path.join(self._output_dir, os.path.basename(image_path))
        out.save(save_image_path)
        return save_image_path


