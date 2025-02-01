import gradio as gr

import modelscope_studio.components.antd as antd
import modelscope_studio.components.base as ms

data = [
    {
        "text": "Racing car sprays burning fuel into crowd. It is a very interesting topic. Why is it interesting? Because it is a very interesting topic.",
    },
    {
        "text": "Japanese princess to wed commoner. It is a very interesting topic. Why is it interesting? Because it is a very interesting topic.",
    },
    {
        "text": "Australian walks 100km after outback crash.",
    },
    {
        "text": "Man charged over missing wedding girl.",
    },
    {
        "text": "Los Angeles battles huge wildfires.",
    },
]

with gr.Blocks() as demo:
    with ms.Application():
        with antd.ConfigProvider():
            antd.Divider("Static Render")
            with antd.List(header="Header", footer="Footer", bordered=True):
                for item in data:
                    with antd.List.Item():
                        antd.Typography.Text("[ITEM]", mark=True)

                        ms.Text(item["text"])


if __name__ == "__main__":
    demo.queue().launch()
