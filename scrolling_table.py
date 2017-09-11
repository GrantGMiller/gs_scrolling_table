from extronlib.system import Wait
from extronlib import event

class ScrollingTable():
    # helper class Cell()**************************************************************
    class Cell():
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

            oldHandlers = {
                'Pressed': self._btn.Pressed,
                'Tapped': self._btn.Tapped,
                'Held': self._btn.Held,
                'Repeated': self._btn.Repeated,
                'Released': self._btn.Released,
                }

            def NewHandler(button, state):
                print(
                    'Cell NewHandler(\n button={}\n state={})\nself._btnNewCallbacks={}'.format(button, state, self._btnNewCallbacks))

                # Handle Mutually exclusive cells
                if self._parent_table._cellMutex == True:
                    for cell in self._parent_table._cells:
                        if cell._row != self._row:
                            cell.SetState(0)
                        else:
                            cell.SetState(1)

                if oldHandlers[state] is not None:
                    oldHandlers[state](button, state)

                if self._btnNewCallbacks[state]:
                    self._btnNewCallbacks[state](self._parent_table, self)

            for state in oldHandlers:
                setattr(self._btn, state, NewHandler)

        def SetText(self, text):
            if self._Text is not text:
                self._btn.SetText(text)
                self._Text = text

        def SetState(self, State):
            if self._btn.State is not State:
                self._btn.SetState(State)

        def SetVisible(self, state):
            if self._btn.Visible is not state:
                self._btn.SetVisible(state)

        def get_col(self):
            return self._col

        def get_row(self):
            return self._row

        def get_value(self):
            return self._Text

        def get_button(self):
            return self._btn

        def __str__(self):
            return 'Cell Object:\nrow={}\ncol={}\nbtn={}'.format(self._row, self._col, self._btn)

    # class ********************************************************************
    def __init__(self):
        '''
        This class represents a spreadsheet with many cells.
        The cells will be filled with data and scrollable on a TLP.
        '''
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

        self._cellMutex = False
        self._freeze = False
        self._hideEmptyRows = False

        # _cell_pressed_callback should accept 2 params; the scrolling table object, and the cell object

        def UpdateTable():
            try:
                self._update_table()
            except Exception as e:
                # need this try/except because current Wait class only shows generic "Wait error" message
                print('Exception in self._update_table()\n', e)

        self._refresh_Wait = Wait(0.2,
                                  UpdateTable)  # This controls how often the table UI gets updated. 0.2 seconds means the TLP has a  max refresh of 5 times per second.
        self._refresh_Wait.Cancel()

        self._initialized = False

    #Setup the table ***********************************************************
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

    def HideEmptyRows(self, state):
        self._hideEmptyRows = state

    def SetCellMutex(self, state):
        # Setting this true will highlight a row when it is pressed
        self._cellMutex = state

    def set_table_header_order(self, header_list=[]):
        # header_list example: ['IP Address', 'Port']
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

        self._refresh_Wait.Restart()

    def register_header_buttons(self, *args):
        '''
        example: ScrollingTable.register_header_buttons(Button(TLP, 1), Button(TLP, 2) )
        '''
        self._header_btns = []
        for arg in args:
            self._header_btns.append(arg)

        @event(self._header_btns, 'Released')
        def header_btn_event(button, state):
            index = self._header_btns.index(button)
            self.sort_by_column(index)

        self._refresh_Wait.Restart()

    def register_row_buttons(self, row_number, *args):
        ''' *args = tuple of Button objects
        example:
        ScrollingTable.register_row(row_number=1, Button(TLP, 1), Button(TLP, 2) )
        '''
        for index, arg in enumerate(args):
            arg.SetText('')
            col_number = index
            self.register_cell(row_number, col_number, btn=arg,
                pressedCallback = self._cell_pressed_callback,
                tappedCallback = self._cell_tapped_callback,
                heldCallback = self._cell_held_callback,
                repeatedCallback = self._cell_repeated_callback,
                releasedCallback = self._cell_released_callback,
                )

        self._refresh_Wait.Restart()

    def add_new_row_data(self, row_dict):
        '''example:
        ScrollingTable.register_data_row({'key1':'value1', 'key2':'value2', ...})
        '''
        print('ScrollingTable.add_new_row_data(row_dict={})'.format(row_dict))
        self._data_rows.append(row_dict)

        for key in row_dict:
            if key not in self._table_header_order:
                self._table_header_order.append(key)

        self.IsScrollable()
        self._initialized = True #assuming that if the user is adding data to the table, then they are done setting up the table
        self._refresh_Wait.Restart()

    def ClearMutex(self):
        if self._cellMutex is True:
            for cell in self._cells:
                cell.SetState(0)

    def clear_all_data(self):
        print('ScrollingTable.clear_all_data()')
        self._data_rows = []
        self.reset_scroll()

        self.ClearMutex()

        self.IsScrollable()
        self._update_table()

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
        self._refresh_Wait.Restart()

    #Manipulating the table data************************************************

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

    def register_cell(self, *args, **kwargs):
        NewCell = self.Cell(self, *args, **kwargs)
        self._cells.append(NewCell)

        self._find_max_row_col()

        self._refresh_Wait.Restart()

    # Displaying the table data ************************************************

    def _find_max_row_col(self):
        '''
        Determine the height and width of the viewable table
        '''
        for cell in self._cells:
            if cell._col > self._max_width:
                self._max_width = cell._col + 1  # self._max_width is width of ui table(not 0 base); 0 means no width

            if cell._row > self._max_height:
                self._max_height = cell._row + 1  # self._max_height is height of ui table(not 0 base); 0 means no height

    def scroll_up(self):
        print('ScrollingTable.scroll_up(self={})'.format(self))
        print('self._current_row_offset=', self._current_row_offset)
        self._current_row_offset -= 1
        if self._current_row_offset < 0:
            self._current_row_offset = 0

        self._update_table()

    def scroll_down(self):
        print('ScrollingTable.scroll_down(self={})'.format(self))
        print('self._current_row_offset=', self._current_row_offset)
        print('self._max_height=', self._max_height)
        print('len(self._data_rows)=', len(self._data_rows))

        max_offset = len(self._data_rows) - self._max_height  #want to show a blank row when we reach the bottom. This is a visual indicator to the user that there is no more data
        if max_offset < 0:
            max_offset = 0
        print('max_offset=', max_offset)

        self._current_row_offset += 1
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

        max_offset = len(self._table_header_order) - self._max_width  # want to show a blank col when we reach the right end. This is a visual indicator to the user that there is no more data
        if max_offset < 0:
            max_offset = 0

        self._current_col_offset += 1
        if self._current_col_offset > max_offset:
            self._current_col_offset = max_offset

        self._update_table()

    def freeze(self, state):
        #If the programmer knows they are going to be updating a bunch of data. They can freeze the table, do all their updates, then unfreeze it.
        #Unfreezing will update the table
        self._freeze = state
        if state is False:
            self._update_table() #immediate update

    def _update_table(self):
        if self._initialized and not self._freeze:
            print('ScrollingTable._update_table()')

            # iterate over all the cell objects
            for cell in self._cells:
                data_row_index = cell._row + self._current_row_offset
                print('cell._row={}, data_row_index={}'.format(cell._row, data_row_index))


                # Is there data for this cell to display?
                if data_row_index < len(self._data_rows):
                    # Yes there is data for this cell to display
                    cell.SetVisible(True)

                    row_dict = self._data_rows[data_row_index]
                    # row_dict holds the data for this row
                    print('cell._row={}\ndata_row_index={}\nrow_dict={}'.format(cell._row, data_row_index, row_dict))

                    col_header_index = cell._col + self._current_col_offset
                    # col_header_index is int() base 0 (left most col is 0)
                    #print('col_header_index=', col_header_index)

                    #print('self._table_header_order=', self._table_header_order)
                    if col_header_index < len(self._table_header_order):
                        col_header_text = self._table_header_order[col_header_index]
                    else:
                        col_header_text = ''
                    #print('col_header=', col_header)

                    #print('row_dict=', row_dict)

                    if col_header_text in row_dict:
                        cell_text = row_dict[col_header_text]  # cell_text holds data for this cell
                    else:
                        # There is no data for this column header
                        cell_text = ''

                    #print('cell_text=', cell_text)

                    cell.SetText(str(cell_text))
                else:
                    # no data for this cell
                    cell.SetText('')

                    if self._hideEmptyRows:
                        if data_row_index >= len(self._data_rows):
                            #There are more rows on the UI than there are rows of data.
                            cell.SetVisible(False)

            # update scroll up/down controls
            if self._scroll_updown_level:
                max_row_offset = len(self._data_rows) - self._max_height
                percent = toPercent(self._current_row_offset, 0, max_row_offset)
                self._scroll_updown_level.SetLevel(percent)

            # update scroll left/right controls
            if self._scroll_leftright_level:
                max_col_offset = len(self._table_header_order) - self._max_width
                percent = toPercent(self._current_col_offset, 0, max_col_offset)
                self._scroll_leftright_level.SetLevel(percent)

            #update col headers
            for headerButton in self._header_btns:
                headerButtonIndex = self._header_btns.index(headerButton)
                headerTextIndex = self._current_col_offset + headerButtonIndex
                if headerTextIndex < len(self._table_header_order):
                    text = self._table_header_order[headerTextIndex]
                    headerButton.SetText(text)

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

    def get_cell_value(self, row_number, col_number):
        for cell in self._cells:
            if cell._row == row_number:
                if cell._col == col_number:
                    return cell._btn.Text

        raise Exception(
            'ScrollingTable.get_cell_value Not found. row_number={}, col_number={}'.format(row_number, col_number))

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

        return result

    def reset_scroll(self):
        self._current_row_offset = 0
        self._refresh_Wait.Restart()

    def sort_by_column_list(self, colNumberList, reverse=False):
        colHeaderList = []
        for colNumber in colNumberList:
            colHeaderList.append(self._table_header_order[colNumber])
        print('colHeaderList=', colHeaderList)

        print('sort_by_column_list before=', self._data_rows)
        self._data_rows = SortListOfDictsByKeys(self._data_rows, colHeaderList, reverse)
        print('sort_by_column_list after=', self._data_rows)

        self._refresh_Wait.Restart()

    def sort_by_column(self, col_number, reverse=False):
        '''
        '''
        key = self._table_header_order[col_number]
        self._data_rows = SortListDictByKey(self._data_rows, key, reverse)
        self._refresh_Wait.Restart()

    def register_scroll_updown_level(self, level):
        # level = extronlib.ui.Level
        self._scroll_updown_level = level

    def register_scroll_up_button(self, button):
        self._scroll_up_button = button

    def register_scroll_down_button(self, button):
        self._scroll_down_button = button

    def register_scroll_updown_label(self, label):
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
        #up/down scroll controls
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

        #left/right scroll controls
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

    aList = aList.copy() #dont want to hurt the users data

    newList = []

    #break list into smaller list
    subList = {
        #'sortKey': [{...}], #all the dict that have the sortKey are in now accessible thru subList['sortKey']
        }

    for d in aList:
        for sortKey in sortKeys:
            if sortKey in d:
                if sortKey not in subList:
                    subList[sortKey] = []

                subList[sortKey].append(d)

    #now all the dicts have been split by sortKey, there are prob duplicates

    #we must now sort the sub list
    for sortKey, l in subList.copy().items():
        l = SortListDictByKey(l, sortKey, reverse)
        subList[sortKey] = l

    #now all the sublist are sorted by their respective keys


    def contains(d, subD):
        #print('contains d={}, subD={}'.format(d, subD))
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
        #l = list of dicts
        #subD = dict
        #returns a list of dicts from within l that contain subD
        #print('getDictWith l={}, subD={}'.format(l2, subD))
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


    #assemble the subList into a single list with the final order
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
                    dictsWithThisValueAndNextValue = getDictWith(aList, {thisKey:thisValue, nextKey:nextValue})
                    for d in dictsWithThisValueAndNextValue:
                        if d not in newList:
                            newList.append(d)

        except Exception as e:
            #print('e=', e)
            #probably on the last index
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

