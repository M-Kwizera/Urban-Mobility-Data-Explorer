# Custom Algorithm Specification: Top-N Min-Heap

## Overview
To fulfill the requirement for a hand-written algorithm without relying on built-in libraries like `heapq` or DataFrame `sort_values`, we implemented a **Custom Min-Heap (`MinHeapTopN`)** to efficiently extract the top $N$ busiest zones by trip count.

## Explanation & Pseudo-Code
Instead of sorting all zones across the entire dataset (which takes $O(M \log M)$ time for $M$ items), a min-heap maintains a fixed-size buffer of size $K$ (where $K = N$). As we stream through the zone counts:
1. If the heap has fewer than $K$ elements, insert the new element.
2. If the heap is full and the new element's count is greater than the smallest element (the root of the min-heap), replace the root and restore heap order via `downheap`.

### Pseudo-Code
```text
class MinHeapTopN:
    initialize heap of capacity K
    
    function push(val, item):
        if length(heap) < K:
            append (val, item) and upheap()
        else if val > heap[0].val:
            heap[0] = (val, item)
            downheap(0)
            
    function upheap(index):
        while index > 0 and heap[index].val < heap[parent].val:
            swap(index, parent)
            index = parent

    function downheap(index):
        find smallest among index, left child, right child
        if smallest != index:
            swap(index, smallest)
            downheap(smallest)