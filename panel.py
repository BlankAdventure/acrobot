# -*- coding: utf-8 -*-
"""
Created on Sat Aug 23 17:02:09 2025

@author: BlankAdventure
"""

import threading
from nicegui import ui
from nicegui.binding import BindableProperty, bind_from
import acrobot

grid_options = {
    'suppressHorizontalScroll': True,
    'scrollbarWidth': 0,  # Optional: set scrollbar width to 0
}


class PanelApp():
    kw_tracker   = BindableProperty(on_change=lambda sender, value: sender.update_keywords(value))
    hist_tracker = BindableProperty(on_change=lambda sender, value: sender.update_history(value))
    
    def __init__(self):
        self.setup_ui()
        bind_from(self_obj=self, self_name='kw_tracker',  other_obj=bot, other_name='keywords', backward=lambda t: t)
        bind_from(self_obj=self, self_name='hist_tracker',other_obj=bot, other_name='history',  backward=lambda t: t)
    
    def setup_ui(self):
        with ui.row():
            
            # === Params UI ===            
            with ui.card().classes('w-80'):
                ui.label('Max history')
                ui.slider(min=0, max=10, step=1, value=acrobot.MAX_HISTORY).props('label-always') \
                    .on('update:model-value', lambda e: ui.notify(e.args),
                        throttle=1.0, leading_events=False).bind_value(acrobot, 'MAX_HISTORY')                

                ui.label('Temperature')
                ui.slider(min=0, max=2, step=0.1, value=acrobot.TEMPERATURE).props('label-always') \
                    .on('update:model-value', lambda e: ui.notify(e.args),
                        throttle=1.0, leading_events=False).bind_value(acrobot, 'TEMPERATURE')                

                ui.label('Thinking tokens')
                ui.slider(min=0, max=1024, step=1, value=0).props('label-always') \
                    .on('update:model-value', lambda e: ui.notify(e.args),
                        throttle=1.0, leading_events=False).bind_value(acrobot, 'THINKING_TOKENS')          
            
            # === Keyword UI ===
            with ui.column():
                self.kw_list = ui.aggrid(
                    auto_size_columns=False,
                    
                    options = {
                    "domLayout": "autoHeight",            
                    'columnDefs': [
                        {'headerName': 'Keywords', 'field': 'keyword','checkboxSelection':True, 'editable':True, 'width': 100, 'resizable':False}],
                    'rowData': [],'rowSelection': 'multiple',                    
                    }).classes('w-48').style('height: unset').on("cellValueChanged", self.keyword_change)
        
                with ui.row():
                    ui.button(icon='add_circle', on_click=self.add_kw_field)
                    ui.button(icon='cancel', on_click=self.del_kw)
            
            # === History UI ===                    
            with ui.column():
                self.hist = ui.aggrid(
                    auto_size_columns=True,
                    options={
                    "domLayout": "autoHeight",            
                    'columnDefs': [{'headerName': 'History', 'field': 'message'}],
                    'rowData': [],
                    }).classes('w-96').style('height: unset')
                
                with ui.row():
                    ui.input(label='Username').props('clearable dense').classes('w-24')
                    ui.input(label='Message').props('clearable dense').classes('w-48')
                    ui.button(icon='add_circle', on_click=self.add_message_dialog).classes('size-8')
                


        self.update_keywords(None)
        self.update_history(None)
    
    async def del_kw(self):
        selected_rows = await self.kw_list.get_selected_rows()        
        to_remove = [k['keyword'] for k in selected_rows]
        bot._del_keywords(to_remove)
        
    
   
    def add_message_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-auto'):
            with ui.row():
                with ui.column():
                    ui.label('Add Message').classes('font-bold w-full border-b')
                    user_input = ui.input(label='Username').props('clearable').classes('w-48')
                    message_input = ui.input(label='Message').props('clearable').classes('w-48')
                    with ui.row():
                        ui.button('Okay') #, on_click=add_rsvp)
                        ui.button('Cancel', on_click=dialog.close)

        dialog.open()
        
        

    def add_kw_field(self):
        ''' Adds an empty field when the "+" button is pressed '''
        self.kw_list.options["rowData"].append({'keyword': ''})
        self.kw_list.update()
        
    
    def update_history(self, val):
        '''
        Called whenever a new message is added to bot.history
        '''
        print(f'called! {val} | {bot.history}')
        
        self.hist.options["rowData"] = [{'message': f"{u} - {m}"} for u, m in bot.history]
        self.hist.update()

    def update_count(self, val):
        print (f'count: {val}')

    def update_keywords(self, val):
        '''
        Called whenever a new keyword is added to bot.keywords
        '''
        self.kw_list.options["rowData"] = [{'keyword': k} for k in bot.keywords]
        self.kw_list.update()
        
    def keyword_change(self, e):
        bot._add_keywords([e.args['value']])
        self.kw_list.update()
        


bot = acrobot.Acrobot()
bot.keywords = {"beer","sister","hash","drunk"}

#thread = threading.Thread(target=bot.start_polling)
#thread.start()




@ui.page('/')
def main():
    PanelApp()


if __name__ in {'__main__', '__mp_main__'}:
    #main()
    # this will block
    ui.run(reload=True)