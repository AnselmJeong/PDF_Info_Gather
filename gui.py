import gradio as gr
import modelscope_studio.components.antd as antd
import modelscope_studio.components.base as ms
from db import set_db_name
from aggregate_snippers import (
    get_theme_items_from_db,
    get_found_themes,
    get_or_create_aggregated_themes,
)

local_answers = {}  # aggregated themes, we have use global variable for Gradio UIs can use.


def get_aggregated_themes(database_name: str, force_new: bool) -> list[dict]:
    try:
        if not database_name:
            antd.message.error("Please enter a database name")
            return gr.Dropdown(choices=[])

        set_db_name(database_name)

        global local_answers
        if local_answers == {}:
            local_answers = get_or_create_aggregated_themes(database_name, force_new=force_new)
        # print(f"local_answers: {local_answers}")

        found_themes = get_found_themes(local_answers)
        new_dropdown = gr.Dropdown(choices=found_themes)
        return new_dropdown
    except ValueError as e:
        # antd.message.error(str(e))
        return gr.Dropdown(choices=[])
    except Exception as e:
        # antd.message.error(f"Failed to connect to database: {str(e)}")
        return gr.Dropdown(choices=[])


def get_content(theme: str) -> str:
    content = get_theme_items_from_db(theme, local_answers)

    return content


with gr.Blocks() as demo:
    content = {}
    with ms.Application():
        with antd.ConfigProvider():
            ###### GUI #######
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("Hello World")
                    database_name = gr.Textbox(
                        label="Database Name", value="", placeholder="Enter database name"
                    )
                    info = gr.Markdown()
                    force_new = gr.Checkbox(label="Force New Aggregation", value=False)
                    agg_button = gr.Button("Aggregate Themes")
                    select_theme = gr.Dropdown(label="Select a theme", interactive=True)
                    select_subtheme = gr.Dropdown(label="Select a subtheme", interactive=True)

                with gr.Column(scale=2):
                    gr.Markdown("Content")

                    @gr.render(inputs=[select_subtheme])
                    def display_content(select_subtheme):
                        subcontent = content.get(select_subtheme, [])
                        # print(f"subcontent: {subcontent}")
                        if isinstance(subcontent, list):
                            antd.Divider(select_subtheme)
                            with antd.List(bordered=True):
                                for package in subcontent:
                                    citations = [package["source_file"]] + package["citations"]
                                    with antd.List.Item():
                                        with gr.Row():
                                            with gr.Column(scale=1, min_width=50):
                                                gr.Markdown("**Snippet**")
                                            with gr.Column(scale=8):
                                                gr.Markdown(package["snippet"])
                                    with antd.List.Item():
                                        with gr.Row():
                                            with gr.Column(scale=1, min_width=50):
                                                gr.Markdown("**Supports**")
                                            with gr.Column(scale=8):
                                                gr.Markdown(package["supports"])
                                    with antd.List.Item():
                                        with gr.Row():
                                            with gr.Column(scale=1, min_width=50):
                                                gr.Markdown("**Rejects**")
                                            with gr.Column(scale=8):
                                                gr.Markdown(package["rejects"])
                                    with antd.List.Item():
                                        with gr.Row():
                                            with gr.Column(scale=1, min_width=50):
                                                gr.Markdown("**Citations**")
                                            with gr.Column(scale=8):
                                                gr.Markdown("\n\n".join(citations))
                                    antd.Divider()

            def update_subtheme(theme: str) -> str:
                global content
                content = get_content(theme)
                subthemes = list(content.keys())
                return gr.Dropdown(choices=subthemes)

            agg_button.click(
                fn=get_aggregated_themes,
                inputs=[database_name, force_new],
                outputs=[select_theme],
            )
            database_name.submit(fn=set_db_name, inputs=[database_name], outputs=[info])
            select_theme.change(
                fn=update_subtheme, inputs=[select_theme], outputs=[select_subtheme]
            )


def main():
    demo.launch()


if __name__ == "__main__":
    main()
