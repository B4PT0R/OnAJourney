from code_editor import code_editor
import streamlit as st

class code_editor_output_parser:
    """
    Parses the raw output of the editor widget.

    This class keeps track of output IDs to ensure events are processed only once.
    It returns a pair (event, content) for each call.

    Attributes:
        keys: dict of keys corresponding to various code editor widgets
        last_id (str): The ID of the last processed output.
        last_code (str): The last processed code content.

    Methods:
        __call__(output): Process the output and return event and content.
    """
    def __init__(self):
        self.editors={}

    def __call__(self,output,key):
        last_id=self.editors.setdefault(key,{}).get('last_id')
        last_code=self.editors.setdefault(key,{}).get('last_code',"")
        if output is None:
            event=None
            content=last_code
        else:
            content=output['text']
            if not output['id']==last_id:
                self.editors[key]['last_code']=output['text']
                self.editors[key]['last_id']=output['id']
                if not output["type"]=='':
                    event=output["type"]
                else:
                    event=None
            else:
                event=None
        return event,content

css_string = '''
    background-color: #bee1e5;

    body > #root .ace-streamlit-dark~& {
    background-color: #262830;
    }

    .ace-streamlit-dark~& span {
    color: #fff;
    opacity: 0.6;
    }

    span {
    color: #000;
    opacity: 0.5;
    }

    .code_editor-info.message {
    width: inherit;
    margin-right: 75px;
    order: 2;
    text-align: center;
    opacity: 0;
    transition: opacity 0.7s ease-out;
    }

    .code_editor-info.message.show {
    opacity: 0.6;
    }

    .ace-streamlit-dark~& .code_editor-info.message.show {
    opacity: 0.5;
    }
    '''

def info_bar(info_name="",info_style=None):
        """
        Returns the bar's configuration as a dictionary.

        Returns:
            dict: A dictionary containing the complete configuration for the bar,
                  including name, CSS, style, and info.
        """
        
        border_radius="0px 0px 8px 8px"

        info_bar = {
            "name": "info_bar",
            "css": css_string,
            "style": {
                        "order": "3",
                        "display": "flex",
                        "flexDirection": "row",
                        "alignItems": "center",
                        "width": "100%",
                        "height": "2.5rem",
                        "padding": "0rem 0.75rem",
                        "borderRadius": border_radius,
                        "zIndex": "9990"
                    },
            "info": [dict(
                name=info_name,
                style=info_style
            )]
        }
        return info_bar

def menu_bar(info_name="",info_style=None):
        """
        Returns the bar's configuration as a dictionary.

        Returns:
            dict: A dictionary containing the complete configuration for the bar,
                  including name, CSS, style, and info.
        """
        
        border_radius="8px 8px 0px 0px"

        menu_bar = {
            "name": "menu_bar",
            "css": css_string,
            "style": {
                        "order": "1",
                        "display": "flex",
                        "flexDirection": "row",
                        "alignItems": "center",
                        "width": "100%",
                        "height": "2.5rem",
                        "padding": "0rem 0.75rem",
                        "borderRadius": border_radius,
                        "zIndex": "9990"
                    },
            "info": [dict(
                name=info_name,
                style=info_style
            )]
        }
        return menu_bar

def button(caption="",icon="Play",event="Play",icon_size="16px", style=None, hover=False,has_caption=True,always_on=False,has_icon=False):
        """
        Returns the control's configuration as a dictionary.

        Returns:
            dict: A dictionary containing the complete configuration for the control,
                  including name, icon, style, and event commands.
        """
        button={
            "name": caption,
            "feather": icon,
            "iconSize":icon_size,
            "primary": hover,
            "hasText": has_caption,
            "alwaysOn": always_on,
            "showWithIcon": has_icon,
            "commands": [
                ["response",event]
            ],
            "style":style
        }
        return button  
    
def editor(code="",lang="python",key=None,**kwargs):
    if not key:
        raise ValueError("No key provided. You must pass a unique key to the editor widget.")
    
    if 'code_editor_output_parser' not in st.session_state:
        st.session_state.code_editor_output_parser=code_editor_output_parser()
    parser=st.session_state.code_editor_output_parser

    menu_bar=kwargs.pop('menu_bar',None)
    info_bar=kwargs.pop('info_bar',None)

    top_borders="8px 8px" if not menu_bar else "0px 0px"
    bot_borders="8px 8px" if not info_bar else "0px 0px"

    borders=f"{top_borders} {bot_borders}"

    options={
        "showLineNumbers":True
    }

    props={ 
        "enableBasicAutocompletion": False, 
        "enableLiveAutocompletion": False, 
        "enableSnippets": False,
    }

    buttons=kwargs.pop('buttons',None) or [{
        "name": "Copy",
        "feather": "Copy",
        "alwaysOn": False,
        "commands": ["copyAll"],
        "style": {"top": "0.46rem", "right": "0.4rem"}
    }]

    options.update(kwargs.pop('options',{}))
    props.update(kwargs.pop('props',{}))

    props.setdefault('style',{}).update(borderRadius=borders)

    handlers={k:v for k,v in kwargs.items() if isinstance(k,str) and k.startswith('on_')}
    rest={k:v for k,v in kwargs.items() if not (isinstance(k,str) and k.startswith('on_'))}

    params=dict(
        code=code,
        lang=lang,
        key=key,
        options=options,
        props=props,
        buttons=buttons,
        **rest
    )

    if info_bar:
         params.update(info=info_bar)
    if menu_bar:
         params.update(menu=menu_bar)

    event,content=parser(code_editor(**params),key)
    if event:
        handler_key=f"on_{event.lower()}"
        if handlers.get(handler_key):
            handlers[handler_key](content)
    return content

if __name__=='__main__':
    
    code=editor("this is a test",key="test1")
    if code:
        st.code(code)

    def on_play(code):
        st.write("hey you clicked on play!")

    code=editor("this is another test",on_play=on_play,buttons=[button("Play",icon='Play',event="Play")], menu_bar=menu_bar(),info_bar=info_bar("Ctrl+Enter to submit",dict(width="100%")), key="test2")
    if code:
        st.code(code)





