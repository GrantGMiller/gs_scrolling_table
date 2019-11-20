import extronlib

try:
    from extronlib_pro import Wait, ProgramLog
except:
    from extronlib.system import Wait, ProgramLog
from extronlib import event
import time

DEBUG = False
oldPrint = print
if not DEBUG:
    print = lambda *a, **k: None  # disable print statements
else:
    def NewPrint(*a, **k):
        oldPrint(*a, **k)
        time.sleep(0.001)


    print = NewPrint


class ScrollingTable:
    # helper class Cell()**************************************************************
    class Cell:
        '''
        Represents a single cell in a scrolling table
        '''

        def __init__(self, parent_table, row, col, btn=None,
                     pressedCallback=None,
                     tappedCallback=None,
                     heldCallback=None,
                     repeatedCallback=None,
                     releasedCallback=None,
                     ):
            print('Cell.__init__(parent_table={}, row={}, col={}, btn={})'.format(parent_table, row, col, btn))
            self._parent_table = parent_table
            self._row = row
            self._col = col
            self._btn = btn
            self._btnNewCallbacks = {
                'Pressed': pressedCallback,
                'Tapped': tappedCallback,
                'Held': heldCallback,
                'Repeated': repeatedCallback,
                'Released': releasedCallback,
            }
            self._Text = ''
            self._btn.SetState(0)

            self.oldHandlers = {
                'Pressed': self._btn.Pressed,
                'Tapped': self._btn.Tapped,
                'Held': self._btn.Held,
                'Repeated': self._btn.Repeated,
                'Released': self._btn.Released,
            }

            def NewScrollTableHandler(button, state):
                print(
                    'Cell NewHandler(\n button={}\n state={})\nself._btnNewCallbacks={}'.format(button, state,
                                                                                                self._btnNewCallbacks))

                # Handle Mutually exclusive cells
                if self._parent_table._rowMutex is True:
                    self._parent_table._rowMutexSelectedRow = self._row + self._parent_table._current_row_offset
                    self._parent_table._update_table()

                print('self.oldHandlers=', self.oldHandlers)
                if self.oldHandlers[state] is not None:
                    if self.oldHandlers[state] is not NewScrollTableHandler:
                        print('calling self.oldHandler[{}]='.format(state), self.oldHandlers[state])
                        print('self.oldHandlers[{}].__name__='.format(state), self.oldHandlers[state].__name__)
                        func = self.oldHandlers[state]
                        print('func=', func)
                        func(button, state)
                        print('oldHandler done')
                    else:
                        # This should not happen
                        print('Error: self.oldHandlers[{}] is NewHandler'.format(state))

                print('self._btnNewCallbacks[state={}]='.format(state), self._btnNewCallbacks[state])
                if self._btnNewCallbacks[state] is not None:
                    print('calling new handler', self._btnNewCallbacks[state])
                    self._btnNewCallbacks[state](self._parent_table, self)
                    print('new handler done')

            for state in self.oldHandlers.keys():
                print('Setting btn={}, state={}, func={}'.format(self._btn, state, NewScrollTableHandler))

                @event(self._btn, state)  # cant use setattr if using extronlib_pro :-(
                def NewHandler53843(button, state):
                    NewScrollTableHandler(button, state)

        def SetText(self, text):
            print('SetText', text, 'self=', self)
            if self._Text is not text:
                self._btn.SetText(text)
                self._Text = text

        def SetState(self, State):
            print('SetState', State, 'self=', self)
            if self._btn.State is not State:
                self._btn.SetState(State)

        def SetVisible(self, state):
            print('SetVisible', state, 'self=', self)
            if self._btn.Visible is not state:
                self._btn.SetVisible(state)

        def get_col(self):
            return self._col

        def get_row(self):
            return self._row

        def GetRowData(self):
            return self.get_row_data()

        def get_row_data(self):
            return self._parent_table.get_row_data_from_cell(self)

        def GetValue(self):
            return self._Text

        def get_value(self):
            return self._Text

        def get_button(self):
            return self._btn

        def get_header(self):
            # print('get_header')
            index = self.get_col()
            # print('index=', index)
            # print('self._parent_table._table_header_order=', self._parent_table._table_header_order)
            return self._parent_table._table_header_order.copy()[self._parent_table._current_col_offset + index]

        @property
        def State(self):
            return self._btn.State

        def __str__(self):
            return '<Cell Object: row={}, col={}, value={}, btn={}>'.format(self._row, self._col, self._Text, self._btn)

    # class ********************************************************************
    def __init__(self):
        '''
        This class represents a spreadsheet with many cells.
        The cells will be filled with data and scrollable on a TLP.
        '''
        self._initialized = False
        self._talbeHasCellWidth = False
        self._tableChangedCallback = None
        self._header_btns = []
        self._cells = []
        self._data_rows = []  # list of dicts. each list element is a row of data. represents the full spreadsheet.
        self._current_row_offset = 0  # indicates the data row in the top left corner
        self._current_col_offset = 0  # indicates the data col in the top left corner
        self._max_height = 0  # height of ui table. 0 = no ui table, 1 = single row ui table, etc...
        self._max_width = 0  # width of ui table. 0 = no ui table, 1 = single column ui table, etc
        self._table_header_order = []

        self._cell_pressed_callback = None
        self._cell_tapped_callback = None
        self._cell_held_callback = None
        self._cell_repeated_callback = None
        self._cell_released_callback = None

        self._scroll_updown_level = None
        self._scroll_up_button = None
        self._scroll_down_button = None
        self._scroll_updown_label = None

        self._scroll_leftright_level = None
        self._scroll_left_button = None
        self._scroll_right_button = None
        self._scroll_leftright_label = None

        self._rowMutex = False
        self._rowMutexSelectedRow = None
        self._freeze = False
        self._hideEmptyRows = False
        self._stateRules = {
            # 'text': int(state),
            # None: int(state), # None is for the 'default' state, which may not exists
            # True: int(state), # State when row is selected
        }
        self._selectedTextState = {}
        # _cell_pressed_callback should accept 2 params; the scrolling table object, and the cell object

        # This controls how often the table UI gets updated. 0.2 seconds means the TLP has a  max refresh of 5 times per second.
        self._waitUpdateTable = Wait(0.2, self._update_table)
        self._waitUpdateTable.Cancel()

        self._initialized = False

    # Setup the table ***********************************************************
    @property
    def CellPressed(self):  # getter
        return self._cell_pressed_callback

    @CellPressed.setter
    def CellPressed(self, func):
        print('CellPressed.setter')
        # func should accept two params the ScrollingTable object and the Cell object
        self._cell_pressed_callback = func
        for cell in self._cells:
            cell._btnNewCallbacks['Pressed'] = func

    @property
    def CellTapped(self):  # getter
        return self._cell_tapped_callback

    @CellTapped.setter
    def CellTapped(self, func):
        print('CellTapped.setter')
        # func should accept two params the ScrollingTable object and the Cell object
        self._cell_tapped_callback = func
        for cell in self._cells:
            cell._btnNewCallbacks['Tapped'] = func

    @property
    def CellHeld(self):  # getter
        return self._cell_held_callback

    @CellHeld.setter
    def CellHeld(self, func):
        print('CellHeld.setter')
        # func should accept two params the ScrollingTable object and the Cell object
        self._cell_held_callback = func
        for cell in self._cells:
            cell._btnNewCallbacks['Held'] = func

    @property
    def CellRepeated(self):  # getter
        return self._cell_repeated_callback

    @CellRepeated.setter
    def CellRepeated(self, func):
        print('CellRepeated.setter')
        # func should accept two params the ScrollingTable object and the Cell object
        self._cell_repeated_callback = func
        for cell in self._cells:
            cell._btnNewCallbacks['Repeated'] = func

    @property
    def CellReleased(self):  # getter
        return self._cell_released_callback

    @CellReleased.setter
    def CellReleased(self, func):
        print('CellReleased.setter')
        # func should accept two params the ScrollingTable object and the Cell object
        self._cell_released_callback = func
        for cell in self._cells:
            cell._btnNewCallbacks['Released'] = func

    @property
    def TabledChanged(self):
        return self._tableChangedCallback

    @TabledChanged.setter
    def TableChanged(self, func):
        self._tableChangedCallback = func

    def SetUpdateDelay(self, t):
        self._waitUpdateTable = Wait(t, self._update_table)

    def HideEmptyRows(self, state):
        self._hideEmptyRows = state

    def SetRowMutex(self, state, showError=True):
        '''
        Setting this true will highlight a row when it is pressed.
        You can also use "ForceRowMutex" to highlight a row just once
        You can use "ClearMutex" to not highlight any rows

        See also the "StateRules" methods for defining what color rows appear as when selected
        :param state: bool
        :return:
        '''
        self._rowMutex = state
        if showError and self._stateRules.get(True, None) is None:
            ProgramLog('Dont forget to use AddSelectedStateRule() and AddNotSelectedStateRule()', 'info')

    def GetSelectedRow(self):
        return self._data_rows[self._rowMutexSelectedRow].copy()

    def GetRowByRowNumber(self, rowNum):
        # this returns the dict for the viewable row rowNum
        print('rowNum=', rowNum)
        print('self._current_row_offset + rowNum=', self._current_row_offset + rowNum)
        print('len(self._data_rows)=', len(self._data_rows))
        if self._current_row_offset + rowNum < len(self._data_rows):
            return self._data_rows[self._current_row_offset + rowNum].copy()

    def _DictContains(self, superDict, subDict):
        # Returns True if superDict contains all the key/values of subDict
        all_keys_match = True
        for key in subDict:
            if key in superDict:
                if superDict[key] != subDict[key]:
                    all_keys_match = False
                    break
            else:
                all_keys_match = False
                break
        print('_DictContains(superDict=', superDict, ', subDict=', subDict, ', all_keys_match=', all_keys_match)
        return all_keys_match

    def GetRowNumber(self, searchRow):
        # searchRow is {}
        # must match exact row
        for rowNumber, row in enumerate(self.get_row_data()):
            if row == searchRow:
                return rowNumber

    def ForceRowMutex(self, whereDict):
        # Force the table to highlight the row that contains whereDict
        print('306 ForceRowMutex(whereDict=', whereDict, 'beforeMutex=', self._rowMutexSelectedRow)
        for rowNumber, rowData in enumerate(self.get_row_data()):
            if self._DictContains(superDict=rowData, subDict=whereDict):
                self._rowMutexSelectedRow = rowNumber
                break

        else:  # only runs if there is no break is hit
            # The whereDict was not found, highlight nothing
            self._rowMutexSelectedRow = None

        self._waitUpdateTable.Restart()

        print('318 afterMutex=', self._rowMutexSelectedRow)

    def set_table_header_order(self, header_list=None):
        # header_list example: ['IP Address', 'Port']
        assert isinstance(header_list, list)
        all_headers = []
        for row in self._data_rows:
            for key in row:
                if key not in all_headers:
                    all_headers.append(key)

        all_headers.sort()  # if some headers are not defined, put them alphabetically

        for key in header_list:
            if key in all_headers:
                all_headers.remove(key)

        # now all_headers contains all headers that are not in header_list
        header_list.extend(all_headers)
        self._table_header_order = header_list

        self._waitUpdateTable.Restart()

    def SetTableHeaderOrder(self, header_list=None):
        # for backwards compatibility
        return self.set_table_header_order(header_list)

    def register_header_buttons(self, *args):
        '''
        example: ScrollingTable.register_header_buttons(Button(TLP, 1), Button(TLP, 2) )
        '''
        self._header_btns = []
        for button in args:
            self._header_btns.append(button)

        @event(self._header_btns, 'Pressed')
        @event(self._header_btns, 'Released')
        def header_btn_event(button, state):
            if state == 'Pressed':
                button.SetState(1)
            elif state == 'Released':
                button.SetState(0)
                index = self._header_btns.index(button) + self._current_col_offset
                self.sort_by_column(index)

        self._waitUpdateTable.Restart()

    def RegisterHeaderButtons(self, *a, **k):
        return self.register_header_buttons(*a, **k)

    def GetRowSize(self):
        # Return how tall the table is (the max num of rows that can be displayed at once
        self._find_max_row_col()
        return self._max_height

    def GetColSize(self):
        # Return how wide the table is (the max num of cols that can be displayed at once
        self._find_max_row_col()
        return self._max_width

    def RegisterRowButtons(self, *a, **k):
        return self.register_row_buttons(*a, **k)

    def register_row_buttons(self, row_number, *args):
        ''' *args = tuple of Button objects
        example:
        ScrollingTable.register_row(row_number=1, Button(TLP, 1), Button(TLP, 2) )
        '''
        for index, arg in enumerate(args):
            arg.SetText('')
            col_number = index
            self.register_cell(row_number, col_number, btn=arg,
                               pressedCallback=self._cell_pressed_callback,
                               tappedCallback=self._cell_tapped_callback,
                               heldCallback=self._cell_held_callback,
                               repeatedCallback=self._cell_repeated_callback,
                               releasedCallback=self._cell_released_callback,
                               )

        self._waitUpdateTable.Restart()

    def add_new_row_data(self, row_dict):
        '''example:
        ScrollingTable.register_data_row({'key1':'value1', 'key2':'value2', ...})
        There are special values including:
        <width {}> - will SetVisible(False) on width cells to the right - this allows you to give the illusion taht a cell is wider than a single cell
            {} is the header name
        '''
        print('ScrollingTable.add_new_row_data(row_dict={})'.format(row_dict))

        if not self._talbeHasCellWidth:
            for key in row_dict:
                if key.startswith('<width'):
                    self._talbeHasCellWidth = True

        self._data_rows.append(row_dict)

        for key in row_dict:
            if key not in self._table_header_order:
                if self._talbeHasCellWidth:
                    if not key.startswith('<width'):
                        # dont add headers with the special "<width..." key
                        self._table_header_order.append(key)
                else:
                    self._table_header_order.append(key)

        self.IsScrollable()
        self._initialized = True  # assuming that if the user is adding data to the table, then they are done setting up the table
        self._waitUpdateTable.Restart()

    def AddNewRowData(self, *a, **k):
        return self.add_new_row_data(*a, **k)

    def ClearMutex(self):
        if self._rowMutex is True:
            for cell in self._cells:
                cell.SetState(0)
        self._rowMutexSelectedRow = None

    def ClearAllData(self, forceRefresh=False):
        return self.clear_all_data(forceRefresh)

    def clear_all_data(self, forceRefresh=False):
        print('ScrollingTable.clear_all_data()')
        self._data_rows = []
        self.reset_scroll()

        self.ClearMutex()

        self.IsScrollable()

        if forceRefresh:
            self._update_table()
        else:
            self._waitUpdateTable.Restart()

    def SetData(self, data):
        '''
        Clears out all old data and replaces it with this data
        :param data: list of dicts
        :return:
        '''
        self._data_rows = data
        self._waitUpdateTable.Restart()

    def update_row_data(self, where_dict, replace_dict):
        '''
        Find a row in self._data_rows that containts all the key/value pairs from where_dict
        replace/append the key/value pairs in that row with the key/values from replace_dict

        '''
        print(
            'ScrollingTable.update_row_data(where_dict={}, replace_dict={})'.format(where_dict, replace_dict))
        # Check the data for a row that containts the key/value pair from where_dict

        if len(self._data_rows) == 0:
            return False

        for row in self._data_rows:
            # verify all the keys from where_dict are in row and the values match
            all_keys_match = True
            for key in where_dict:
                if key in row:
                    if where_dict[key] != row[key]:
                        all_keys_match = False
                        break
                else:
                    all_keys_match = False
                    break

            if all_keys_match:
                # All the key/values from where_dict match row, update row with replace dict values
                for key in replace_dict:
                    row[key] = replace_dict[key]

        self.IsScrollable()
        self._waitUpdateTable.Restart()

    def UpdateRowData(self, *a, **k):
        return self.update_row_data(*a, **k)

    # Manipulating the table data************************************************
    def HasRow(self, where_dict):
        return self.has_row(where_dict)

    def has_row(self, where_dict):
        print('ScrollingTable.has_row(where_dict={})'.format(where_dict))
        print('self._data_rows=', self._data_rows)
        # Check the data for a row that containts the key/value pair from where_dict

        if len(self._data_rows) == 0:
            print('ScrollingTable.has_row return False')
            return False

        for row in self._data_rows:
            # verify all the keys from where_dict are in row and the values match
            all_keys_match = True
            for key in where_dict:
                if key in row:
                    if where_dict[key] != row[key]:
                        all_keys_match = False
                        break
                else:
                    all_keys_match = False
                    break

            if all_keys_match:
                print('ScrollingTable.has_row return True')
                return True

        print('ScrollingTable.has_row return False')
        return False

    def delete_row(self, where_dict):
        if not self.has_row(where_dict):
            return
        else:
            for row in self._data_rows.copy():
                # verify all the keys from where_dict are in row and the values match
                all_keys_match = True
                for key in where_dict:
                    if key in row:
                        if where_dict[key] != row[key]:
                            all_keys_match = False
                            break
                    else:
                        all_keys_match = False
                        break

                if all_keys_match:
                    # all keys match in this row. remove it
                    print('ScrollingTable.delete_row\nremoving row={}'.format(row))
                    self._data_rows.remove(row)

        self.IsScrollable()
        self._update_table()

    def DeleteRow(self, where_dict):
        return self.delete_row(where_dict)

    def register_cell(self, *args, **kwargs):
        NewCell = self.Cell(self, *args, **kwargs)
        self._cells.append(NewCell)

        self._find_max_row_col()

        self._waitUpdateTable.Restart()

    # Displaying the table data ************************************************

    def _find_max_row_col(self):
        '''
        Determine the height and width of the viewable table
        '''
        print('_find_max_row_col old_width={}, old_height={}'.format(self._max_width, self._max_height))
        for cell in self._cells:
            if cell._col > self._max_width:
                self._max_width = cell._col + 1  # self._max_width is width of ui table(not 0 base); 0 means no width

            if cell._row > self._max_height:
                self._max_height = cell._row + 1  # self._max_height is height of ui table(not 0 base); 0 means no height

        print('_find_max_row_col new_width={}, new_height={}'.format(self._max_width, self._max_height))

    def ScrollUp(self, *a, **k):
        return self.scroll_up(*a, **k)

    def scroll_up(self, count=1):
        print('ScrollingTable.scroll_up(self={})'.format(self))
        print('self._current_row_offset=', self._current_row_offset)
        self._current_row_offset -= count
        if self._current_row_offset < 0:
            self._current_row_offset = 0

        self._update_table()

    def ScrollDown(self, *a, **k):
        return self.scroll_down(*a, **k)

    def scroll_down(self, count=1):
        print('ScrollingTable.scroll_down(self={})'.format(self))
        print('self._current_row_offset=', self._current_row_offset)
        print('self._max_height=', self._max_height)
        print('len(self._data_rows)=', len(self._data_rows))

        max_offset = len(
            self._data_rows) - self._max_height  # want to show a blank row when we reach the bottom. This is a visual indicator to the user that there is no more data
        if max_offset < 0:
            max_offset = 0
        print('max_offset=', max_offset)

        self._current_row_offset += count
        if self._current_row_offset > max_offset:
            self._current_row_offset = max_offset

        self._update_table()

    def scroll_left(self):
        print('ScrollingTable.scroll_left(self={})'.format(self))
        self._current_col_offset -= 1
        if self._current_col_offset < 0:
            self._current_col_offset = 0

        self._update_table()

    def scroll_right(self):
        print('ScrollingTable.scroll_right(self={})'.format(self))

        max_offset = len(
            self._table_header_order) - self._max_width  # want to show a blank col when we reach the right end. This is a visual indicator to the user that there is no more data
        if max_offset < 0:
            max_offset = 0

        self._current_col_offset += 1
        if self._current_col_offset > max_offset:
            self._current_col_offset = max_offset

        self._update_table()

    def freeze(self, state):
        # If the programmer knows they are going to be updating a bunch of data. They can freeze the table, do all their updates, then unfreeze it.
        # Unfreezing will update the table
        self._freeze = state
        if state is False:
            self._update_table()  # immediate update

    def _update_table(self):
        if self._initialized and not self._freeze:
            print('631 ScrollingTable._update_table()')
            print('self._current_row_offset=', self._current_row_offset)
            print('self._rowMutexSelectedRow=', self._rowMutexSelectedRow)
            print('self._rowMutex=', self._rowMutex)

            # iterate over all the cell objects
            for cell in self._cells:

                data_row_index = cell._row + self._current_row_offset
                print('640 cell._row={}, data_row_index={}'.format(cell._row, data_row_index))

                # Is there data for this cell to display?
                if data_row_index < len(self._data_rows):
                    print('644 data_row_index=', data_row_index)
                    # Yes there is data for this cell to display
                    cell.SetVisible(True)

                    row_dict = self._data_rows[data_row_index]
                    # row_dict holds the data for this row
                    print(
                        '649 cell._row={}\ndata_row_index={}\nrow_dict={}'.format(cell._row, data_row_index, row_dict))

                    col_header_index = cell._col + self._current_col_offset
                    # col_header_index is int() base 0 (left most col is 0)
                    # print('col_header_index=', col_header_index)

                    # print('self._table_header_order=', self._table_header_order)
                    if col_header_index < len(self._table_header_order):
                        col_header_text = self._table_header_order[col_header_index]
                    else:
                        col_header_text = ''
                    # print('col_header=', col_header)

                    # print('row_dict=', row_dict)

                    if col_header_text in row_dict:
                        cell_text = row_dict[col_header_text]  # cell_text holds data for this cell
                    else:
                        # There is no data for this column header
                        cell_text = ''
                    cell_text = str(cell_text)
                    # print('cell_text=', cell_text)

                    cell.SetText(cell_text)

                    # Set the state if applicable
                    if cell_text in self._selectedTextState:
                        print('676 self._rowMutexSelectedRow=', self._rowMutexSelectedRow)
                        if self._rowMutexSelectedRow is None:
                            if isinstance(self._selectedTextState[cell_text], list):
                                cell.SetBlinking('Slow', self._selectedTextState[cell_text])
                            else:
                                cell.SetState(self._selectedTextState[cell_text])

                        else:
                            # row mutex is True
                            # this should not happen
                            pass

                    elif cell_text in self._stateRules:
                        print('688 self._rowMutexSelectedRow=', self._rowMutexSelectedRow)
                        if self._rowMutexSelectedRow is None:
                            if isinstance(self._stateRules[cell_text], list):
                                cell.SetBlinking('Slow', self._stateRules[cell_text])
                            else:
                                cell.SetState(self._stateRules[cell_text])
                        else:
                            # Cell mutex is True
                            # If the row is not selected, then set the state according to the rule
                            # If the row is selected,
                            if cell.get_row() + self._current_row_offset == self._rowMutexSelectedRow:
                                # row is selected
                                selectedState = self._stateRules.get(True, None)
                                if selectedState is not None:
                                    cell.SetState(selectedState)
                                else:
                                    pass
                            else:
                                # row is not selected
                                if isinstance(self._stateRules[cell_text], list):
                                    cell.SetBlinking('Slow', self._stateRules[cell_text])
                                else:
                                    cell.SetState(self._stateRules[cell_text])

                    else:
                        # This text is not in the _stateRules
                        print('716 self._stateRules=', self._stateRules)
                        if None in self._stateRules:
                            # A Default state exists
                            print('715 self._rowMutexSelectedRow=', self._rowMutexSelectedRow)
                            if self._rowMutexSelectedRow is None:
                                cell.SetState(self._stateRules[None])
                            else:
                                # Cell mutex is True
                                # If the row is not selected, then set the state according to the rule
                                # If the row is selected, dont do anything
                                if cell.get_row() + self._current_row_offset == self._rowMutexSelectedRow:
                                    selectedState = self._stateRules.get(True, None)
                                    if selectedState is not None:
                                        cell.SetState(selectedState)
                                    else:
                                        pass
                                else:
                                    cell.SetState(self._stateRules[None])

                        else:
                            print('735')
                            # there are no stateRules, assume 0=nsel, 1=sel
                            if self._rowMutexSelectedRow is None:
                                cell.SetState(0)
                            else:  # _rowMutexSelectedRow = int(selected)
                                if cell.get_row() + self._current_row_offset == self._rowMutexSelectedRow:
                                    cell.SetState(1)
                                else:
                                    cell.SetState(0)

                else:
                    print('748 no data for this cell', cell)
                    # no data for this cell
                    cell.SetText('')

                    if self._hideEmptyRows:
                        if data_row_index >= len(self._data_rows):
                            # There are more rows on the UI than there are rows of data.
                            cell.SetVisible(False)

            # update scroll up/down controls
            if self._scroll_updown_level:
                max_row_offset = len(self._data_rows) - self._max_height
                percent = toPercent(self._current_row_offset, 0, max_row_offset)
                if isinstance(self._scroll_updown_level, extronlib.ui.Level):
                    self._scroll_updown_level.SetLevel(percent)
                elif isinstance(self._scroll_updown_level, extronlib.ui.Slider):
                    self._scroll_updown_level.SetFill(percent)

            # update scroll left/right controls
            if self._scroll_leftright_level:
                max_col_offset = len(self._table_header_order) - self._max_width
                percent = toPercent(self._current_col_offset, 0, max_col_offset)
                self._scroll_leftright_level.SetLevel(percent)

            # update col headers
            for headerButton in self._header_btns:
                headerButtonIndex = self._header_btns.index(headerButton)
                headerTextIndex = self._current_col_offset + headerButtonIndex
                if headerTextIndex < len(self._table_header_order):
                    text = self._table_header_order[headerTextIndex]
                    headerButton.SetText(text)

            if self._talbeHasCellWidth:
                self._SetCellWidthVisiblity()

            # Notify the user that a change has been applied to the table
            if callable(self._tableChangedCallback):
                self._tableChangedCallback()

    def _SetCellWidthVisiblity(self):
        print('_SetCellWidthVisiblity')
        for rowNum in range(self._max_height):
            rowDict = self.GetRowByRowNumber(rowNum)
            if rowDict is not None:
                skip = 0
                for colNum in range(self._max_width):
                    print('727 rowNum={}, colNum={}'.format(rowNum, colNum))
                    if skip > 0:
                        print('skip rowNum={}, colNum={}'.format(rowNum, colNum))
                        skip -= 1
                        continue

                    cell = self.GetCell(rowNum, colNum)
                    if cell is not None:
                        widthKey = '<width {}>'.format(cell.get_header())
                        print('widthKey=', widthKey, ', rowDict=', rowDict)
                        if widthKey in rowDict:
                            cellWidth = rowDict[widthKey]
                            print('cellWidth=', cellWidth)
                            if cellWidth > 1:
                                skip = cellWidth - 1
                                # hide cells to right
                                for i in range(1, cellWidth):
                                    nextCellColNum = cell.get_col() + i
                                    if nextCellColNum < self._max_width:
                                        print('670 row_dict=', rowDict)
                                        print('this cell col=', cell.get_col())
                                        print('next cell col=', nextCellColNum)
                                        self.GetCell(cell.get_row(), nextCellColNum).SetVisible(False)
                            else:
                                print('749 else')
                                cell.SetVisible(True)
                        else:
                            print('752 else')
                            # assume width of 1
                            cell.SetVisible(True)


            else:  # rowDict is None
                # assume width of 1
                cell.SetVisible(True)

    def get_column_buttons(self, col_number):
        # returns all buttons in the column.
        # Note: they may not be in order
        btn_list = []

        for cell in self._cells:
            if cell._col == col_number:
                btn_list.append(cell._btn)

        return btn_list

    def get_row_from_button(self, button):
        for cell in self._cells:
            if cell._btn == button:
                return cell._row

        raise Exception('Button {} not found in table'.format(button))

    def GetCell(self, rowNum, colNum):
        for cell in self._cells:
            if cell.get_col() == colNum:
                if cell.get_row() == rowNum:
                    return cell

    def get_cell_value(self, row_number, col_number):
        print('ScrollingTable.get_cell_value(row_number={}, col_number={})'.format(row_number, col_number))
        for cell in self._cells:
            print('cell=', cell)
            if cell._row == row_number:
                if cell._col == col_number:
                    return cell._Text

        return None

    def get_row_data_from_cell(self, cell):
        # returns a dict of the row data
        rowIndex = cell.get_row()
        dataIndex = rowIndex + self._current_row_offset
        return self._data_rows[dataIndex]

    def get_row_data(self, where_dict=None):
        # returns a list of dicts that match whereDict
        # if where_dict == None, will return all data
        if where_dict == None:
            where_dict = {}

        result = []

        for row in self._data_rows:
            # verify all the keys from where_dict are in row and the values match
            all_keys_match = True
            for key in where_dict:
                if key in row:
                    if where_dict[key] != row[key]:
                        all_keys_match = False
                        break
                else:
                    all_keys_match = False
                    break

            if all_keys_match:
                # All the key/values from where_dict match row, update row with replace dict values
                result.append(row)

        return result.copy()

    def GetRowData(self, where_dict=None):
        return self.get_row_data(where_dict)

    def reset_scroll(self, forceUpdate=False):
        self._current_row_offset = 0
        if forceUpdate:
            self._update_table()
        else:
            self._waitUpdateTable.Restart()

    def ResetScroll(self):
        self.reset_scroll()

    def SortCustom(self, func):
        '''

        :param func: function compatible with the sorted(key=) builtin
        :return:
        '''
        oldData = self._data_rows.copy()
        newData = sorted(oldData, key=func)
        self._data_rows = newData

    def sort_by_column_list(self, colNumberList, reverse=False):
        colHeaderList = []
        for colNumber in colNumberList:
            colHeaderList.append(self._table_header_order[colNumber])
        print('colHeaderList=', colHeaderList)

        print('sort_by_column_list before=', self._data_rows)
        self._data_rows = SortListOfDictsByKeys(self._data_rows, colHeaderList, reverse)
        print('sort_by_column_list after=', self._data_rows)

        self._waitUpdateTable.Restart()

    def sort_by_column(self, col_number, reverse=False):
        '''
        '''
        key = self._table_header_order[col_number]
        self._data_rows = SortListDictByKey(self._data_rows, key, reverse)
        self._waitUpdateTable.Restart()

    def sort_by_column_name(self, colName, reverse=False):
        '''
        '''
        self._data_rows = SortListDictByKey(self._data_rows, colName, reverse)
        self._waitUpdateTable.Restart()

    def SortByColumnName(self, *a, **k):
        self.sort_by_column_name(*a, **k)

    def RegisterScrollUpDownLevel(self, level):
        try:
            if isinstance(level, extronlib.ui.Slider):
                level.Changed = lambda s, value: self.SetScrollPercent(value)
        except:
            pass
        return self.register_scroll_updown_level(level)

    def SetScrollPercent(self, percent):
        total = len(self._data_rows)
        index = total * (percent / 100)
        self._current_row_offset = index
        self._update_table()

    def register_scroll_updown_level(self, level):
        # This will automatically SetVisible the button if the table is too long
        # level = extronlib.ui.Level
        self._scroll_updown_level = level

    def RegisterScrollUpButton(self, button):
        return self.register_scroll_up_button(button)

    def register_scroll_up_button(self, button):
        # This will automatically SetVisible the button if the table is too long
        self._scroll_up_button = button

    def RegisterScrollDownButton(self, button):
        return self.register_scroll_down_button(button)

    def register_scroll_down_button(self, button):
        # This will automatically SetVisible the button if the table is too long
        self._scroll_down_button = button

    def RegisterScrollUpDownLabel(self, label):
        return self.register_scroll_updown_label(label)

    def register_scroll_updown_label(self, label):
        # This will automatically SetVisible the button if the table is too long
        self._scroll_updown_label = label

    def register_scroll_leftright_level(self, level):
        # level = extronlib.ui.Level
        self._scroll_leftright_level = level

    def register_scroll_left_button(self, button):
        self._scroll_left_button = button

    def register_scroll_right_button(self, button):
        self._scroll_right_button = button

    def register_scroll_leftright_label(self, label):
        self._scroll_leftright_label = label

    def IsScrollable(self):
        '''
        basically if there are 10 rows on your TLP, but you only have 5 rows of data, then you dont need to show scroll buttons, hide the controls assiciated with scrolling
        '''
        # up/down scroll controls
        if len(self._data_rows) > self._max_height:
            if self._scroll_updown_level is not None:
                self._scroll_updown_level.SetVisible(True)

            if self._scroll_up_button is not None:
                self._scroll_up_button.SetVisible(True)

            if self._scroll_down_button is not None:
                self._scroll_down_button.SetVisible(True)

            if self._scroll_updown_label is not None:
                self._scroll_updown_label.SetVisible(True)

        else:
            if self._scroll_updown_level is not None:
                self._scroll_updown_level.SetVisible(False)

            if self._scroll_up_button is not None:
                self._scroll_up_button.SetVisible(False)

            if self._scroll_down_button is not None:
                self._scroll_down_button.SetVisible(False)

            if self._scroll_updown_label is not None:
                self._scroll_updown_label.SetVisible(False)

        # left/right scroll controls
        if len(self._table_header_order) > self._max_width:
            if self._scroll_leftright_level is not None:
                self._scroll_leftright_level.SetVisible(True)

            if self._scroll_left_button is not None:
                self._scroll_left_button.SetVisible(True)

            if self._scroll_right_button is not None:
                self._scroll_right_button.SetVisible(True)

            if self._scroll_leftright_label is not None:
                self._scroll_leftright_label.SetVisible(True)

        else:
            if self._scroll_leftright_level is not None:
                self._scroll_leftright_level.SetVisible(False)

            if self._scroll_left_button is not None:
                self._scroll_left_button.SetVisible(False)

            if self._scroll_right_button is not None:
                self._scroll_right_button.SetVisible(False)

            if self._scroll_leftright_label is not None:
                self._scroll_leftright_label.SetVisible(False)

    def AddSelectedTextStateRule(self, text, state):
        self._selectedTextState[text] = state
        self._update_table()

    def GetSelectedTextStateRules(self):
        return self._selectedTextState.copy()

    def RemoveSelectedTextStateRule(self, text):
        self._selectedTextState.pop(text, None)
        self._update_table()

    def ClearSelectedTextStateRules(self):
        self._selectedTextState = {}
        self._update_table()

    def ClearAllStateRules(self):
        self._selectedTextState = {}
        self._stateRules = {}
        self._update_table()

    def AddNotSelectedTextStateRule(self, text, state):
        '''
        This sets a state rule for when the row is not selected, and the text matches
        Has precedence over "AddNotSelectedStateRule"
        Example: self.AddNotSelectedTextStateRule('Connected', 1) will SetState(1) on the button if the text shows disconnected
        :param text: str
        :param state: int or list of ints
        :return:
        '''
        self._stateRules[text] = state

    def AddNotSelectedStateRule(self, state):
        '''
        This adds a state rule for when the row is not selected.
        :param state: int
        :return:
        '''
        self._stateRules[None] = state

    def AddSelectedStateRule(self, state):
        '''
        This adds a state rule for when the row is selected.
        Has precedence over "AddNotSelectedTextStateRule"
        :param state: int
        :return:
        '''
        self._stateRules[True] = state

    def MoveRow(self, whereDict, direction=None):
        '''
        This method will move a row up or down on the table
        :param whereDict: dict or part of the dict that needs to be moved
        :param direction: int - positive means move down, negative means move up, 0 is ignored
        :return:
        '''
        print('MoveRow(whereDict={}, direction={})'.format(whereDict, direction))
        if direction in [None, 0]:
            return
        row = self.get_row_data(whereDict)  # returns a list of dicts
        if len(row) > 0:
            row = row[0]  # only worry about the first one
        rowCurrentIndex = self._data_rows.index(row)

        if row not in self._data_rows:
            print('MoveRow() No row to move with row={}, direction={}'.format(row, direction))
            return  # cant move it if its not there

        self._data_rows.remove(row)  # Temporarily remove the row from the data set
        rowNewIndex = rowCurrentIndex + direction  # This is where the row will be placed
        self._data_rows.insert(rowNewIndex, row)
        self._update_table()

    def MoveRowIndex(self, whereDict, newIndex):
        '''
        This method will move a row to the newIndex position
        :param whereDict:
        :param newIndex:
        :return:
        '''
        print('MoveRowIndex(whereDict={}, newIndex={})'.format(whereDict, newIndex))
        row = self.get_row_data(whereDict)  # returns a list of dicts
        if len(row) > 0:
            row = row[0]  # only worry about the first one

        if row not in self._data_rows:
            print('MoveRowIndex() No row to move with row={}, newIndex={}'.format(row, newIndex))
            return  # cant move it if its not there

        self._data_rows.remove(row)
        self._data_rows.insert(newIndex, row)
        self._update_table()

    def MoveRowRelative(self, moveDict, relativeDict, position='Above'):
        '''
        This method will move the moveDict next to the relativeDict
        :param moveDict:
        :param relativeDict:
        :param position: 'Above' means put moveDict on top of relativeDict, 'Below' means put moveDict below relativeDict
        :return:
        '''
        print('MoveRowRelative(moveDict={}, relativeDict={}, position={})'.format(moveDict, relativeDict, position))
        relativeRow = self.get_row_data(relativeDict)  # returns a list of dicts
        if len(relativeRow) > 0:
            relativeRow = relativeRow[0]  # only worry about the first one
        else:
            print('MoveRowRelative() relativeRow not found. relativeDict={}'.format(relativeDict))
            return  # the relative row was not found. do nothing.

        moveRow = self.get_row_data(moveDict)  # returns a list of dicts
        if len(moveRow) > 0:
            moveRow = moveRow[0]

        if moveRow not in self._data_rows:
            print('MoveRowRelative() No row to move with moveRow={}, moveDict={}'.format(moveRow, moveDict))
            return  # cant move it if its not there

        self._data_rows.remove(moveRow)

        # We remove the moveRow first... now the relativeIndex is correct
        relativeIndex = self._data_rows.index(relativeRow)

        if position == 'Above':
            self._data_rows.insert(relativeIndex, moveRow)
        elif position == 'Below':
            self._data_rows.insert(relativeIndex + 1, moveRow)

        self._update_table()


def SortListDictByKey(aList, sortKey, reverse=False):
    '''
    aList = list of dicts
    sortKeys = list key from dict. the dicts will be sorted in this order
    reverse =  Used to sort a-z(False) or z-a(True)
    returns a new list with the items(dicts) sorted by key

    Example
    aList = [{'Value', '1'}, {'Value', '3'}, {'Value', '2'}...]
    newList = SortListOfDictsByKey(aList, 'Value')
    print(newList)
    >>[{'Value', '1'}, {'Value', '2'}, {'Value', '3'}...]

    newList = SortListOfDictsByKey(aList, 'Value', 'decending')
    print(newList)
    >>[{'Value', '3'}, {'Value', '2'}, {'Value', '1'}...]

    '''

    if not isinstance(reverse, bool):
        raise Exception('Reverse parameter must be type bool')

    return sorted(aList, key=lambda d: str(d[sortKey]), reverse=reverse)


def SortListOfDictsByKeys(aList, sortKeys=None, reverse=False):
    print('SortListOfDictsByKeys(aList={}, sortKeys={}, reverse={})'.format(aList, sortKeys, reverse))
    '''
    aList = list of dicts
    sortKeys = list of keys to sort by
    reverse = bool to sort a-z(True) or z-a(False)
    returns a new list of dicts

    Example:
    #a list filled with dicts that are not in any particular order
    theList = [
        {'valueB': 1, 'valueC': 2, 'valueA': 1} ,
        {'valueB': 0, 'valueC': 1, 'valueA': 0} ,
        {'valueB': 2, 'valueC': 9, 'valueA': 0} ,
        {'valueB': 2, 'valueC': 1, 'valueA': 2} ,
        {'valueB': 1, 'valueC': 1, 'valueA': 2} ,
        {'valueB': 1, 'valueC': 2, 'valueA': 0} ,
        {'valueB': 0, 'valueC': 2, 'valueA': 2} ,
        {'valueB': 0, 'valueC': 7, 'valueA': 1} ,
        {'valueB': 2, 'valueC': 5, 'valueA': 1} ,
        ]

    newList = SortListOfDictsByKeys(theList, ['valueA', 'valueC'])
    print(newList)
    >>>
    [
        {'valueB': 0, 'valueC': 1, 'valueA': 0} ,
        {'valueB': 1, 'valueC': 2, 'valueA': 0} ,
        {'valueB': 2, 'valueC': 9, 'valueA': 0} ,
        {'valueB': 1, 'valueC': 2, 'valueA': 1} ,
        {'valueB': 2, 'valueC': 5, 'valueA': 1} ,
        {'valueB': 0, 'valueC': 7, 'valueA': 1} ,
        {'valueB': 2, 'valueC': 1, 'valueA': 2} ,
        {'valueB': 1, 'valueC': 1, 'valueA': 2} ,
        {'valueB': 0, 'valueC': 2, 'valueA': 2} ,
    ]

    Notice the dicts are organized by valueA, when valueA is the same, then they are sorted by valueC

    '''
    if len(aList) == 0:
        return aList

    if sortKeys is None:
        sortKeys = []

    missingKeys = []
    for d in aList:
        for key in d:
            if key not in sortKeys and key not in missingKeys:
                missingKeys.append(key)

    sortKeys.extend(missingKeys)

    aList = aList.copy()  # dont want to hurt the users data

    newList = []

    # break list into smaller list
    subList = {
        # 'sortKey': [{...}], #all the dict that have the sortKey are in now accessible thru subList['sortKey']
    }

    for d in aList:
        for sortKey in sortKeys:
            if sortKey in d:
                if sortKey not in subList:
                    subList[sortKey] = []

                subList[sortKey].append(d)

    # now all the dicts have been split by sortKey, there are prob duplicates

    # we must now sort the sub list
    for sortKey, l in subList.copy().items():
        l = SortListDictByKey(l, sortKey, reverse)
        subList[sortKey] = l

    # now all the sublist are sorted by their respective keys

    def contains(d, subD):
        # print('contains d={}, subD={}'.format(d, subD))
        containsAllKeys = True
        for key in subD:
            if key not in d:
                containsAllKeys = False
                return False

        if containsAllKeys:
            for key in subD:
                if d[key] != subD[key]:
                    return False

        return True

    def getDictWith(l2, subD):
        # l = list of dicts
        # subD = dict
        # returns a list of dicts from within l that contain subD
        # print('getDictWith l={}, subD={}'.format(l2, subD))
        result = []

        for d in l2:
            if contains(d, subD):
                result.append(d)
        return result

    def getAllValuesOfKey(listOfDicts, key):
        values = []
        for d in listOfDicts:
            if d[key] not in values:
                values.append(d[key])

        return values

    for key in subList:
        print('subList[{}] = {}'.format(key, subList[key]))

    # assemble the subList into a single list with the final order
    newList = []

    for thisKey in sortKeys:
        thisList = subList[thisKey]
        thisIndex = sortKeys.index(thisKey)
        try:
            nextIndex = thisIndex + 1
            nextKey = sortKeys[nextIndex]
            nextList = subList[nextKey]

            print('\n thisKey={}, thisList={}'.format(thisKey, thisList))
            print('nextKey={}, nextList={}'.format(nextKey, nextList))

            for thisValue in getAllValuesOfKey(thisList, thisKey):
                for nextValue in getAllValuesOfKey(nextList, nextKey):
                    dictsWithThisValueAndNextValue = getDictWith(aList, {thisKey: thisValue, nextKey: nextValue})
                    for d in dictsWithThisValueAndNextValue:
                        if d not in newList:
                            newList.append(d)

        except Exception as e:
            # print('e=', e)
            # probably on the last index
            for d in thisList:
                if d not in newList:
                    newList.append(d)
                    pass

    return newList


def toPercent(Value, Min=0, Max=100):
    '''
    This function will take the Value, Min and Max and return a percentage
    :param Value: float
    :param Min: float
    :param Max: float
    :return: float from 0.0 to 100.0
    '''
    try:
        if Value < Min:
            return 0
        elif Value > Max:
            return 100

        TotalRange = Max - Min
        # print('TotalRange=', TotalRange)

        FromMinToValue = Value - Min
        # print('FromMinToValue=', FromMinToValue)

        Percent = (FromMinToValue / TotalRange) * 100

        return Percent
    except Exception as e:
        # print(e)
        # ProgramLog('gs_tools toPercent Erorr: {}'.format(e), 'error')
        return 0
