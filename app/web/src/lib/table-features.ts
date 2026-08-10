import {
  columnVisibilityFeature,
  createSortedRowModel,
  rowSortingFeature,
  sortFns,
  tableFeatures,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table";

export const sortableTableFeatures = tableFeatures({
  columnVisibilityFeature,
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns,
});

export type SortableTableFeatures = typeof sortableTableFeatures;

// ColumnDef is invariant in its value type, so a heterogeneous array of
// createColumnHelper accessors only unifies through the wildcard.
export type SortableColumnDefs<TData extends RowData> = Array<
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ColumnDef<SortableTableFeatures, TData, any>
>;
