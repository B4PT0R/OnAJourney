from code_editor import code_editor
import streamlit as st

class editor_output_parser:
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
    
def editor(code="",lang="python",key=None,**kwargs):
    if not key:
        raise ValueError("No key provided. You must pass a unique key to the editor widget.")
    
    if 'code_editor_output_parser' not in st.session_state:
        st.session_state.code_editor_output_parser=editor_output_parser()
    parser=st.session_state.code_editor_output_parser

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

    event,content=parser(code_editor(code=code,lang=lang,key=key,options=options,props=props,buttons=buttons, **kwargs),key)
    if event:
        handler_key=f"on_{event}"
        if kwargs.get(handler_key):
            kwargs[handler_key](content)
    return content

if __name__=='__main__':
    
    code=editor("this is a test",key="test1")
    if code:
        st.code(code)

    code=editor("this is another test",key="test2")
    if code:
        st.code(code)





