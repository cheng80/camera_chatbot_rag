# Graph-lite ERD

```text
models
  │
  └── supports_model
        │
features ── belongs_to_category ── categories
   │
   ├── source_document ── documents
   ├── source_page ── pages
   └── alias_of ── aliases
```

Current local Panasonic graph-lite artifact:

```text
feature_wiki.json: 4,388 weak feature entries, 26,130 model source refs
graph_lite.json: 25,234 nodes, 95,057 edges
node kinds: feature, alias, category, model, document, page
edge kinds: alias_of, belongs_to_category, supports_model, source_document, source_page
```
