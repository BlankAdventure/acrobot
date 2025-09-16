# -*- coding: utf-8 -*-
"""
Created on Sat Aug 23 17:02:09 2025

@author: BlankAdventure
"""


from nicegui import ui, ElementFilter
from nicegui.binding import BindableProperty, bind_from
import acrobot


def borders_on():
    ElementFilter(kind=ui.column).style( 'border: solid; border-width: thin; border-color: red;');
    ElementFilter(kind=ui.row).style(    'border: solid; border-width: thin; border-color: green');
    ElementFilter(kind=ui.label).style(  'border: solid; border-width: thin; border-color: yellow');
    ElementFilter(kind=ui.element).style('border: solid; border-width: thin; border-color: black');

class PanelApp():
    kw_tracker   = BindableProperty(on_change=lambda sender,_: sender.update_keywords())
    hist_tracker = BindableProperty(on_change=lambda sender,_: sender.update_history())
    
    def __init__(self, bot):
        self.bot = bot
        self.setup_ui()
        
        #borders_on()
        bind_from(self_obj=self, self_name='kw_tracker',  other_obj=self.bot, other_name='keywords', backward=lambda t: t)
        bind_from(self_obj=self, self_name='hist_tracker',other_obj=self.bot, other_name='history',  backward=lambda t: t)
    
    def setup_ui(self) -> None:
        with ui.element():
            ui.label('Acrobot Adjusterizer').classes('text-center text-xl bg-slate-300 mb-2')
            with ui.row():
                
                # === Params UI ===            
                with ui.card().classes('w-64'):
                    ui.label('Max history')
                    ui.slider(min=0, max=10, step=1, value=acrobot.MAX_HISTORY).props('label-always') \
                        .on('update:model-value', throttle=1.0, leading_events=False) \
                        .bind_value(acrobot, 'MAX_HISTORY')                
    
                    ui.label('Temperature')
                    ui.slider(min=0, max=2, step=0.1, value=acrobot.TEMPERATURE).props('label-always') \
                        .on('update:model-value', throttle=1.0, leading_events=False) \
                        .bind_value(acrobot, 'TEMPERATURE')                
    
                    ui.label('Thinking tokens')
                    ui.slider(min=0, max=1024, step=1, value=0).props('label-always') \
                        .on('update:model-value', throttle=1.0, leading_events=False) \
                        .bind_value(acrobot, 'THINKING_TOKENS')          
                
                # === Keyword UI ===
                with ui.column().classes('p-0 gap-0'):
                    self.kw_list = ui.aggrid(
                        auto_size_columns=False,
                        
                        options = {
                        "domLayout": "autoHeight",            
                        'columnDefs': [
                            {'headerName': 'Keywords', 'field': 'keyword','checkboxSelection':True,'width': 150, 'resizable':False}],
                        'rowData': [],'rowSelection': 'multiple',                    
                        }).classes('w-40').style('height: unset')
            
                    with ui.row():
                        self.kw_input = ui.input(label='keyword').props('clearable dense').classes('w-40')
                    with ui.row().classes('pt-2'):
                        ui.button(icon='add_circle', on_click=lambda: self.add_keyword(self.kw_input.value)).props('size=md') #flat
                        ui.button(icon='cancel', on_click=self.del_kw).props('size=md')
                
                # === History UI ===                    
                with ui.column().classes():
                    self.hist = ui.aggrid(
                        auto_size_columns=True,
                        options={
                        "domLayout": "autoHeight",            
                        'columnDefs': [{'headerName': 'History', 'field': 'message'}],
                        'rowData': [],
                        }).classes('w-96').style('height: unset')
                    
                    with ui.row():
                        self.user_input = ui.input(label='Username').props('clearable dense').classes('w-24')
                        self.msg_input = ui.input(label='Message').props('clearable dense').classes('w-48')
                        ui.button(icon='add_circle', on_click=self.add_message).props('size=md') #.classes('size-8')

        self.update_keywords()
        self.update_history()    

    async def del_kw(self) -> None:
        '''
        Called upon deleting keywords from the list
        '''        
        selected_rows = await self.kw_list.get_selected_rows()        
        to_remove = [k['keyword'] for k in selected_rows]
        if to_remove:
            self.bot._del_keywords(to_remove)       
    
    def update_history(self) -> None:
        '''
        Called whenever a new message is added to bot.history
        '''
        
        self.hist.options["rowData"] = [{'message': f"{u} - {m}"} for u, m in self.bot.history]
        self.hist.update()

    def add_message(self) -> None:
        username = self.user_input.value
        message = self.msg_input.value        
        if username and message:        
            self.bot._update_history(username, message)
            
        self.user_input.value = None
        self.msg_input.value = None

    def update_keywords(self) -> None:
        '''
        Called whenever a new keyword is added to bot.keywords
        '''
        self.kw_list.options["rowData"] = [{'keyword': k} for k in self.bot.keywords]
        self.kw_list.update()
        
    def add_keyword(self, kw: str) -> None:
        '''
        Called whenever a new keyword is added through the UI.
        '''
        if kw:
            self.bot._add_keywords([kw])
        self.kw_input.value = None
     
def run_webhook(webhook_url: str|None, ip_addr: str, port: int)->None:
    import uvicorn
    
    @ui.page('/panel')
    def index():
        PanelApp(bot)
    
    bot = acrobot.Acrowebhook(webhook_url=webhook_url)
    bot.keywords = {"beer","sister","hash","drunk"}            
    ui.run_with(bot)    
    uvicorn.run(bot,host=ip_addr,port=port) #this will block

def run_polling()->None:
    import threading 
    
    @ui.page('/panel')
    def index():
        PanelApp(bot)

    bot = acrobot.Acrobot()
    bot.keywords = {"beer","sister","hash","drunk"}
    
    # start the bot loop in a thread so it doesn't block the ui
    thread = threading.Thread(target=bot.start_polling)
    thread.start()
    ui.run(reload=False) #this will block

def run_ui():
    @ui.page('/')
    def index():
        PanelApp(bot)

    bot = acrobot.Acrobot()
    bot.keywords = {"beer","sister","hash","drunk"}
    

    
if __name__ in {'__main__', '__mp_main__'}:
    run_ui()
    ui.run(reload=True)

