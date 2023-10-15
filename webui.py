from python_hijack import *

import gradio as gr
import random
import time
import shared
import modules.path
import fooocus_version
import modules.html
import modules.async_worker as worker
import modules.flags as flags
import modules.gradio_hijack as grh
import modules.advanced_parameters as advanced_parameters
import args_manager

from modules.sdxl_styles import legal_style_names, aspect_ratios
from modules.private_logger import get_current_html_path


def generate_clicked(*args):
    execution_start_time = time.perf_counter()

    yield gr.update(visible=True, value=modules.html.make_progress_html(1, 'Initializing ...')), \
        gr.update(visible=True, value=None), \
        gr.update(visible=False)

    worker.buffer.append(list(args))
    finished = False

    while not finished:
        time.sleep(0.01)
        if len(worker.outputs) > 0:
            flag, product = worker.outputs.pop(0)
            if flag == 'preview':
                percentage, title, image = product
                yield gr.update(visible=True, value=modules.html.make_progress_html(percentage, title)), \
                    gr.update(visible=True, value=image) if image is not None else gr.update(), \
                    gr.update(visible=False)
            if flag == 'results':
                yield gr.update(visible=False), \
                    gr.update(visible=False), \
                    gr.update(visible=True, value=product)
                finished = True

    execution_time = time.perf_counter() - execution_start_time
    print(f'Total time: {execution_time:.2f} seconds')
    return


shared.gradio_root = gr.Blocks(
    title=f'Fooocus {fooocus_version.version} ' + ('' if args_manager.args.preset is None else args_manager.args.preset),
    css=modules.html.css).queue()

with shared.gradio_root:
    with gr.Row():
        with gr.Column():
            progress_window = grh.Image(label='预览', show_label=True, height=640, visible=False)
            progress_html = gr.HTML(value=modules.html.make_progress_html(32, 'Progress 32%'), visible=False, elem_id='progress-bar', elem_classes='progress-bar')
            gallery = gr.Gallery(label='图集', show_label=False, object_fit='contain', height=720, visible=True, elem_classes='resizable_area')
            with gr.Row(elem_classes='type_row'):
                with gr.Column(scale=0.85):
                    prompt = gr.Textbox(show_label=False, placeholder="输入对生成图片的场景描述.",
                                        value=modules.path.default_positive_prompt,
                                        container=False, autofocus=True, elem_classes='type_row', lines=2)
                with gr.Column(scale=0.15, min_width=0):
                    translate_button = gr.Button(label="转译", value="转译", elem_classes='type_row', visible=True)
            with gr.Row(elem_classes='type_row'):
                with gr.Column(scale=0.85):
                    prompt = gr.Textbox(show_label=False, placeholder="输入提示词。",
                                        value=modules.path.default_positive_prompt,
                                        container=False, autofocus=True, elem_classes='type_row', lines=1024)
                with gr.Column(scale=0.15, min_width=0):
                    run_button = gr.Button(label="生成", value="生成", elem_classes='type_row', visible=True)
                    skip_button = gr.Button(label="跳过", value="跳过", elem_classes='type_row_half', visible=False)
                    stop_button = gr.Button(label="终止", value="终止", elem_classes='type_row_half', visible=False)

                    def stop_clicked():
                        import fcbh.model_management as model_management
                        shared.last_stop = 'stop'
                        model_management.interrupt_current_processing()
                        return [gr.update(interactive=False)] * 2

                    def skip_clicked():
                        import fcbh.model_management as model_management
                        shared.last_stop = 'skip'
                        model_management.interrupt_current_processing()
                        return

                    stop_button.click(stop_clicked, outputs=[skip_button, stop_button], queue=False)
                    skip_button.click(skip_clicked, queue=False)
            with gr.Row(elem_classes='advanced_check_row'):
                input_image_checkbox = gr.Checkbox(label='输入图片', value=False, container=False, elem_classes='min_check')
                advanced_checkbox = gr.Checkbox(label='高级选项', value=False, container=False, elem_classes='min_check')
            with gr.Row(visible=False) as image_input_panel:
                with gr.Tabs():
                    with gr.TabItem(label='强化与变换') as uov_tab:
                        with gr.Row():
                            with gr.Column():
                                uov_input_image = grh.Image(label='将图片拖入这里', source='upload', type='numpy')
                            with gr.Column():
                                uov_method = gr.Radio(label='强化(Vary)与变换(Upscale)：', choices=flags.uov_list, value=flags.disabled)
                                gr.HTML('<a href="https://github.com/lllyasviel/Fooocus/discussions/390" target="_blank">\U0001F4D4 参考文档</a>')
                    with gr.TabItem(label='依图生图') as ip_tab:
                        with gr.Row():
                            ip_images = []
                            ip_types = []
                            ip_stops = []
                            ip_weights = []
                            ip_ctrls = []
                            ip_ad_cols = []
                            for _ in range(4):
                                with gr.Column():
                                    ip_image = grh.Image(label='Image', source='upload', type='numpy', show_label=False, height=300)
                                    ip_images.append(ip_image)
                                    ip_ctrls.append(ip_image)
                                    with gr.Column(visible=False) as ad_col:
                                        with gr.Row():
                                            default_end, default_weight = flags.default_parameters[flags.default_ip]

                                            ip_stop = gr.Slider(label='终止在', minimum=0.0, maximum=1.0, step=0.001, value=default_end)
                                            ip_stops.append(ip_stop)
                                            ip_ctrls.append(ip_stop)

                                            ip_weight = gr.Slider(label='权重', minimum=0.0, maximum=2.0, step=0.001, value=default_weight)
                                            ip_weights.append(ip_weight)
                                            ip_ctrls.append(ip_weight)

                                        ip_type = gr.Radio(label='类型', choices=flags.ip_list, value=flags.default_ip, container=False)
                                        ip_types.append(ip_type)
                                        ip_ctrls.append(ip_type)

                                        ip_type.change(lambda x: flags.default_parameters[x], inputs=[ip_type], outputs=[ip_stop, ip_weight], queue=False, show_progress=False)
                                    ip_ad_cols.append(ad_col)
                        ip_advanced = gr.Checkbox(label='高级选项', value=False, container=False)
                        gr.HTML('* \"Image Prompt\" is powered by Fooocus Image Mixture Engine (v1.0.1). <a href="https://github.com/lllyasviel/Fooocus/discussions/557" target="_blank">\U0001F4D4 参考文档</a>')

                        def ip_advance_checked(x):
                            return [gr.update(visible=x)] * len(ip_ad_cols) + \
                                [flags.default_ip] * len(ip_types) + \
                                [flags.default_parameters[flags.default_ip][0]] * len(ip_stops) + \
                                [flags.default_parameters[flags.default_ip][1]] * len(ip_weights)

                        ip_advanced.change(ip_advance_checked, inputs=ip_advanced,
                                           outputs=ip_ad_cols + ip_types + ip_stops + ip_weights, queue=False)

                    with gr.TabItem(label='修补与融合（测试）') as inpaint_tab:
                        inpaint_input_image = grh.Image(label='将图片拖入这里', source='upload', type='numpy', tool='sketch', height=500, brush_color="#FFFFFF")
                        gr.HTML('扩图 (<a href="https://github.com/lllyasviel/Fooocus/discussions/414" target="_blank">\U0001F4D4 参考文档</a>):')
                        outpaint_selections = gr.CheckboxGroup(choices=['Left', 'Right', 'Top', 'Bottom'], value=[], label='Outpaint', show_label=False, container=False)
                        gr.HTML('* \"Inpaint or Outpaint\" is powered by the sampler \"DPMPP Fooocus Seamless 2M SDE Karras Inpaint Sampler\" (beta)')

            switch_js = "(x) => {if(x){setTimeout(() => window.scrollTo({ top: 850, behavior: 'smooth' }), 50);}else{setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }), 50);} return x}"
            down_js = "() => {setTimeout(() => window.scrollTo({ top: 850, behavior: 'smooth' }), 50);}"

            input_image_checkbox.change(lambda x: gr.update(visible=x), inputs=input_image_checkbox, outputs=image_input_panel, queue=False, _js=switch_js)
            ip_advanced.change(lambda: None, queue=False, _js=down_js)

            current_tab = gr.Textbox(value='uov', visible=False)

            default_image = None

            def update_default_image(x):
                global default_image
                if isinstance(x, dict):
                    default_image = x['image']
                else:
                    default_image = x
                return

            def clear_default_image():
                global default_image
                default_image = None
                return

            uov_input_image.upload(update_default_image, inputs=uov_input_image, queue=False)
            inpaint_input_image.upload(update_default_image, inputs=inpaint_input_image, queue=False)

            uov_input_image.clear(clear_default_image, queue=False)
            inpaint_input_image.clear(clear_default_image, queue=False)

            uov_tab.select(lambda: ['uov', default_image], outputs=[current_tab, uov_input_image], queue=False, _js=down_js)
            inpaint_tab.select(lambda: ['inpaint', default_image], outputs=[current_tab, inpaint_input_image], queue=False, _js=down_js)
            ip_tab.select(lambda: 'ip', outputs=[current_tab], queue=False, _js=down_js)

        with gr.Column(scale=0.5, visible=False) as right_col:
            with gr.Tab(label='设置'):
                performance_selection = gr.Radio(label='性能（Speed速度，Quality质量）', choices=['Speed', 'Quality'], value='Speed')
                aspect_ratios_selection = gr.Radio(label='宽高比', choices=list(aspect_ratios.keys()),
                                                   value=modules.path.default_aspect_ratio, info='宽 × 高')
                image_number = gr.Slider(label='出图数量', minimum=1, maximum=32, step=1, value=2)
                negative_prompt = gr.Textbox(label='反向提示词', show_label=True, placeholder="输入提示词。",
                                             info='描述你不想看到的内容', lines=2,
                                             value=modules.path.default_negative_prompt)
                seed_random = gr.Checkbox(label='随机种子', value=True)
                image_seed = gr.Number(label='种子', value=0, precision=0, visible=False)

                def random_checked(r):
                    return gr.update(visible=not r)

                def refresh_seed(r, s):
                    if r:
                        return random.randint(1, 1024*1024*1024)
                    else:
                        return s

                seed_random.change(random_checked, inputs=[seed_random], outputs=[image_seed], queue=False)

                gr.HTML(f'<a href="/file={get_current_html_path()}" target="_blank">\U0001F4DA History Log</a>')

            with gr.Tab(label='风格'):
                style_selections = gr.CheckboxGroup(show_label=False, container=False,
                                                    choices=legal_style_names,
                                                    value=modules.path.default_styles,
                                                    label='图片风格')
            with gr.Tab(label='模型'):
                with gr.Row():
                    base_model = gr.Dropdown(label='SDXL基础模型', choices=modules.path.model_filenames, value=modules.path.default_base_model_name, show_label=True)
                    refiner_model = gr.Dropdown(label='SDXL精炼模型', choices=['None'] + modules.path.model_filenames, value=modules.path.default_refiner_model_name, show_label=True)
                with gr.Accordion(label='LoRAs', open=True):
                    lora_ctrls = []
                    for i in range(5):
                        with gr.Row():
                            lora_model = gr.Dropdown(label=f'SDXL LoRA {i+1}', choices=['None'] + modules.path.lora_filenames, value=modules.path.default_lora_name if i == 0 else 'None')
                            lora_weight = gr.Slider(label='权重', minimum=-2, maximum=2, step=0.01, value=modules.path.default_lora_weight)
                            lora_ctrls += [lora_model, lora_weight]
                with gr.Row():
                    model_refresh = gr.Button(label='刷新', value='\U0001f504 全部刷新', variant='secondary', elem_classes='refresh_button')
            with gr.Tab(label='高级'):
                sharpness = gr.Slider(label='采样的清晰度', minimum=0.0, maximum=30.0, step=0.001, value=2.0,
                                      info='越高图像和纹理越清晰')
                guidance_scale = gr.Slider(label='提示词引导系数', minimum=1.0, maximum=30.0, step=0.01, value=modules.path.default_cfg_scale,
                                      info='提示词作用的强度，越高风格越干净、生动、更具艺术感')

                gr.HTML('<a href="https://github.com/lllyasviel/Fooocus/discussions/117" target="_blank">\U0001F4D4 参考文档</a>')
                dev_mode = gr.Checkbox(label='开发者模式', value=False, container=False)

                with gr.Column(visible=False) as dev_tools:
                    with gr.Tab(label='开发者调试工具'):
                        adm_scaler_positive = gr.Slider(label='正向ADM指导缩放', minimum=0.1, maximum=3.0,
                                                        step=0.001, value=1.5, info='用于乘以正向ADM的缩放器 (使用1.0以禁用). ')
                        adm_scaler_negative = gr.Slider(label='负向ADM指导缩放', minimum=0.1, maximum=3.0,
                                                        step=0.001, value=0.8, info='用于乘以负向ADM的缩放器 (使用1.0以禁用). ')
                        adm_scaler_end = gr.Slider(label='ADM指导结束步长', minimum=0.0, maximum=1.0,
                                                   step=0.001, value=0.3,
                                                   info='从正向/负向ADM结束指导的时间')

                        refiner_swap_method = gr.Dropdown(label='精炼交换方式', value='joint',
                                                          choices=['joint', 'separate', 'vae'])

                        adaptive_cfg = gr.Slider(label='CFG模拟TSNR', minimum=1.0, maximum=30.0, step=0.01, value=7.0,
                                                 info='Enabling Fooocus\'s implementation of CFG mimicking for TSNR '
                                                      '（实际生效需满足真实CFG大于模拟CFG的条件）')
                        sampler_name = gr.Dropdown(label='采样器', choices=flags.sampler_list,
                                                   value=modules.path.default_sampler,
                                                   info='仅在非修复模式下有效')
                        scheduler_name = gr.Dropdown(label='调度器', choices=flags.scheduler_list,
                                                     value=modules.path.default_scheduler,
                                                     info='采样器调度程序')

                        overwrite_step = gr.Slider(label='强制覆盖采样步长',
                                                   minimum=-1, maximum=200, step=1, value=-1,
                                                   info='设为-1以禁用。用于开发者调试')
                        overwrite_switch = gr.Slider(label='强制覆盖优化开关步长',
                                                     minimum=-1, maximum=200, step=1, value=-1,
                                                     info='设为-1以禁用。用于开发者调试')
                        overwrite_width = gr.Slider(label='强制覆盖生成宽度',
                                                    minimum=-1, maximum=2048, step=1, value=-1,
                                                    info='设为-1以禁用。用于开发者调试')
                        overwrite_height = gr.Slider(label='Forced Overwrite of Generating Height',
                                                     minimum=-1, maximum=2048, step=1, value=-1,
                                                     info='设为-1以禁用。用于开发者调试')
                        overwrite_vary_strength = gr.Slider(label='强制覆盖变换的去噪强度',
                                                            minimum=-1, maximum=1.0, step=0.001, value=-1,
                                                            info='设为负数以禁用。用于开发者调试')
                        overwrite_upscale_strength = gr.Slider(label='Forced Overwrite of Denoising Strength of "Upscale"',
                                                               minimum=-1, maximum=1.0, step=0.001, value=-1,
                                                               info='设为负数以禁用。用于开发者调试')

                        inpaint_engine = gr.Dropdown(label='修补引擎', value='v1', choices=['v1', 'v2.5'],
                                                     info='Fooocus修补引擎版本')

                    with gr.Tab(label='调试控制'):
                        debugging_cn_preprocessor = gr.Checkbox(label='ControlNets的调试预处理器', value=False)

                        mixing_image_prompt_and_vary_upscale = gr.Checkbox(label='混合图像提示和可变/放大',
                                                                           value=False)
                        mixing_image_prompt_and_inpaint = gr.Checkbox(label='混合图像提示和修复',
                                                                      value=False)

                        controlnet_softness = gr.Slider(label='ControlNet柔化', minimum=0.0, maximum=1.0,
                                                        step=0.001, value=0.25,
                                                        info='类似于A1111中的控制模式（使用0.0禁用）')

                        with gr.Tab(label='锐化Canny',):
                            canny_low_threshold = gr.Slider(label='锐化的低阈值', minimum=1, maximum=255,
                                                            step=1, value=64)
                            canny_high_threshold = gr.Slider(label='锐化的高阈值', minimum=1, maximum=255,
                                                             step=1, value=128)

                    with gr.Tab(label='FreeU'):
                        freeu_enabled = gr.Checkbox(label='Enabled', value=False)
                        freeu_b1 = gr.Slider(label='B1', minimum=0, maximum=2, step=0.01, value=1.01)
                        freeu_b2 = gr.Slider(label='B2', minimum=0, maximum=2, step=0.01, value=1.02)
                        freeu_s1 = gr.Slider(label='S1', minimum=0, maximum=4, step=0.01, value=0.99)
                        freeu_s2 = gr.Slider(label='S2', minimum=0, maximum=4, step=0.01, value=0.95)
                        freeu_ctrls = [freeu_enabled, freeu_b1, freeu_b2, freeu_s1, freeu_s2]

                adps = [adm_scaler_positive, adm_scaler_negative, adm_scaler_end, adaptive_cfg, sampler_name,
                        scheduler_name, overwrite_step, overwrite_switch, overwrite_width, overwrite_height,
                        overwrite_vary_strength, overwrite_upscale_strength,
                        mixing_image_prompt_and_vary_upscale, mixing_image_prompt_and_inpaint,
                        debugging_cn_preprocessor, controlnet_softness, canny_low_threshold, canny_high_threshold,
                        inpaint_engine, refiner_swap_method]
                adps += freeu_ctrls

                def dev_mode_checked(r):
                    return gr.update(visible=r)


                dev_mode.change(dev_mode_checked, inputs=[dev_mode], outputs=[dev_tools], queue=False)

                def model_refresh_clicked():
                    modules.path.update_all_model_names()
                    results = []
                    results += [gr.update(choices=modules.path.model_filenames), gr.update(choices=['None'] + modules.path.model_filenames)]
                    for i in range(5):
                        results += [gr.update(choices=['None'] + modules.path.lora_filenames), gr.update()]
                    return results

                model_refresh.click(model_refresh_clicked, [], [base_model, refiner_model] + lora_ctrls, queue=False)

        advanced_checkbox.change(lambda x: gr.update(visible=x), advanced_checkbox, right_col, queue=False)

        ctrls = [
            prompt, negative_prompt, style_selections,
            performance_selection, aspect_ratios_selection, image_number, image_seed, sharpness, guidance_scale
        ]

        ctrls += [base_model, refiner_model] + lora_ctrls
        ctrls += [input_image_checkbox, current_tab]
        ctrls += [uov_method, uov_input_image]
        ctrls += [outpaint_selections, inpaint_input_image]
        ctrls += ip_ctrls

        run_button.click(lambda: (gr.update(visible=True, interactive=True), gr.update(visible=True, interactive=True), gr.update(visible=False), []), outputs=[stop_button, skip_button, run_button, gallery])\
            .then(fn=refresh_seed, inputs=[seed_random, image_seed], outputs=image_seed)\
            .then(advanced_parameters.set_all_advanced_parameters, inputs=adps)\
            .then(fn=generate_clicked, inputs=ctrls, outputs=[progress_html, progress_window, gallery])\
            .then(lambda: (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)), outputs=[run_button, stop_button, skip_button])


shared.gradio_root.launch(
    inbrowser=args_manager.args.auto_launch,
    server_name=args_manager.args.listen,
    server_port=args_manager.args.port,
    share=args_manager.args.share,
    root_path=args_manager.args.webroot
)
