import type { Stock, StockList, StockListItemListResponse } from '@/types';
import stockListReducer, {
  fetchListStocks,
  setCurrentList,
} from '../stockListSlice';

const makeList = (id: number): StockList => ({
  id,
  user_id: 'user-1',
  name: `List ${id}`,
  is_default: id === 1,
  sort_order: id,
  stocks_count: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
});

const makeStock = (id: number): Stock => ({
  id,
  symbol: `STOCK${id}`,
  market: 'US',
  name: `Stock ${id}`,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
});

const makeResponse = (listId: number, stock: Stock): StockListItemListResponse => ({
  items: [stock],
  total: 1,
  list_id: listId,
  list_name: `List ${listId}`,
});

describe('stockListSlice list stock requests', () => {
  it('clears the previous list stocks immediately when the selected list changes', () => {
    const firstList = makeList(1);
    const secondList = makeList(2);
    const firstStock = makeStock(101);

    let state = stockListReducer(undefined, setCurrentList(firstList));
    state = stockListReducer(state, fetchListStocks.pending('request-1', firstList.id));
    state = stockListReducer(
      state,
      fetchListStocks.fulfilled(makeResponse(firstList.id, firstStock), 'request-1', firstList.id)
    );

    expect(state.currentListStocks).toEqual([firstStock]);

    state = stockListReducer(state, setCurrentList(secondList));

    expect(state.currentList).toEqual(secondList);
    expect(state.currentListStocks).toEqual([]);
    expect(state.currentListStocksListId).toBeNull();
  });

  it('ignores an older response that resolves after the latest selected list', () => {
    const firstStock = makeStock(101);
    const secondStock = makeStock(202);

    let state = stockListReducer(undefined, fetchListStocks.pending('request-1', 1));
    state = stockListReducer(state, fetchListStocks.pending('request-2', 2));
    state = stockListReducer(
      state,
      fetchListStocks.fulfilled(makeResponse(2, secondStock), 'request-2', 2)
    );
    state = stockListReducer(
      state,
      fetchListStocks.fulfilled(makeResponse(1, firstStock), 'request-1', 1)
    );

    expect(state.currentListStocks).toEqual([secondStock]);
    expect(state.currentListStocksListId).toBe(2);
    expect(state.loading).toBe(false);
  });

  it('invalidates an in-flight response when selection changes before a new request starts', () => {
    const firstStock = makeStock(101);

    let state = stockListReducer(undefined, setCurrentList(makeList(1)));
    state = stockListReducer(state, fetchListStocks.pending('request-1', 1));
    state = stockListReducer(state, setCurrentList(makeList(2)));
    state = stockListReducer(
      state,
      fetchListStocks.fulfilled(makeResponse(1, firstStock), 'request-1', 1)
    );

    expect(state.currentList?.id).toBe(2);
    expect(state.currentListStocks).toEqual([]);
    expect(state.currentListStocksListId).toBeNull();
  });

  it('clears stocks whose recorded list does not match a re-selected current list', () => {
    const currentList = makeList(1);
    const otherStock = makeStock(202);

    let state = stockListReducer(undefined, setCurrentList(currentList));
    state = stockListReducer(state, fetchListStocks.pending('request-2', 2));
    state = stockListReducer(
      state,
      fetchListStocks.fulfilled(makeResponse(2, otherStock), 'request-2', 2)
    );

    expect(state.currentList?.id).toBe(1);
    expect(state.currentListStocksListId).toBe(2);

    state = stockListReducer(state, setCurrentList(currentList));

    expect(state.currentListStocks).toEqual([]);
    expect(state.currentListStocksListId).toBeNull();
  });
});
