# **Split Shared NASTRAN PIDs Across Disconnected FE Bodies**

This repository contains an ANSA Python script that **automatically detects disconnected FE bodies** and **splits shared NASTRAN property IDs (PIDs)** by cloning properties and reassigning elements.  
It ensures that **each FE body receives a unique property**, preventing cross‑body PID contamination and improving model consistency.

## **Purpose**

In many FE models, especially those imported from CAD or legacy preprocessors, **multiple disconnected FE bodies may share the same PID**.  
This causes problems when:

- Assigning materials  
- Assigning thickness  
- Running deck‑specific checks  
- Exporting to solvers  
- Performing FE → CAD mapping  
- Managing part‑based workflows  

This script **automates the cleanup** by:

- Detecting disconnected FE bodies using **node adjacency**
- Identifying PIDs used across multiple bodies
- Cloning the property for each additional body
- Reassigning elements to the new PID

## **How It Works**

### 1. **Collect FE Elements**
The script gathers all **SHELL** and **SOLID** elements from the active NASTRAN deck.

### 2. **Detect FE Bodies**
Bodies are detected using:

- `base.Or()`
- `base.Neighb("ALL")`
- Visibility‑filtered element collection

Each connected region becomes one FE body.

### 3. **Map PIDs to Bodies**
For each body, the script builds:

- A list of PIDs used  
- A mapping of PID → elements  

Then it identifies PIDs shared across multiple bodies.

### 4. **Clone Properties**
For each shared PID:

- The first body keeps the original PID  
- All other bodies receive a **cloned property**  
- The clone copies all valid card fields except metadata and ANSA‑specific UI fields

### 5. **Reassign Elements**
Elements belonging to the additional bodies are reassigned to the new PID.

## **Key Features**

- **Automatic FE body detection** (no need to manually group elements)
- **Robust property cloning** with fallback logic
- **Safe reassignment** of elements to new PIDs
- **Supports SHELL and SOLID elements**
- **Dry‑run mode** for previewing changes
- **Clear console output** summarizing all operations

## **Script Structure**

| Component | Description |
|----------|-------------|
| `collect_all_fe_elements()` | Collects all FE elements from the deck |
| `find_fe_bodies()` | Detects disconnected FE bodies |
| `get_element_pid()` | Extracts PID from element |
| `clone_property()` | Creates a cloned property with copied card fields |
| `reassign_elements_to_pid()` | Reassigns elements to new PID |
| `main()` | Orchestrates the full workflow |


## **Usage**

### **Inside ANSA**

1. Open ANSA  
2. Go to:  
   **Scripts → Run Script**  
3. Select this Python file  
4. View results in the console

### **Dry Run Mode**

Set:

```python
DRY_RUN = True
```

This will show what changes *would* happen without modifying the model.

## **Example Output**

```
Found 3 disconnected FE body(ies).

Shared PIDs detected across bodies:
  PID 1201 used by bodies: [1, 3]
  PID 4500 used by bodies: [2, 3]

Resolving shared PIDs...
  Cloned PID 1201 -> 9876 for body 3 and reassigned 152 elements
  Cloned PID 4500 -> 9877 for body 3 and reassigned 89 elements

Summary:
  Shared PIDs resolved: 2
  Elements reassigned: 241
  Created 2 new property(ies).
```

## **When to Use This Script**

Use this script when:

- Importing FE models from CAD  
- Cleaning up legacy models  
- Preparing models for solver export  
- Ensuring each FE body has unique material/thickness properties  
- Avoiding PID conflicts during FE → CAD mapping  

## **Limitations**

- Works only on **NASTRAN** deck  
- Only clones properties; does not modify materials  
- Does not merge bodies — only splits PIDs  
- Requires ANSA Python environment  

## **License**

MIT License — feel free to use, modify, and contribute.
