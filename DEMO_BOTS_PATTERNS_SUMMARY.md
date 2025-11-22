# 📚 Complete Demo Bots Patterns Analysis

## Overview
Analyzed **11 complete demo bot examples** from Zoho SalesIQ to identify best practices and patterns.

---

## 🎯 **Universal Patterns Across All Bots**

### **1. Response Structure**
All bots use consistent response patterns:

```deluge
response = Map();
response.put("action", "reply");  // or "context", "forward", "end"
response.put("replies", {...});   // Collection of strings or Maps
response.put("suggestions", {...}); // Optional: Collection of action strings
```

### **2. Replies Format - Two Patterns**

#### **Pattern A: Simple Text Replies (Most Common)**
```deluge
response.put("replies", {"Hello!", "How can I help?"});
// OR
response.put("replies", {{"text": "Hello!"}});
```

#### **Pattern B: Replies with Images (Cards)**
```deluge
replies = Collection();
replies.insert({"text": "Item 1", "image": "https://..."});
replies.insert({"text": "Item 2", "image": "https://..."});
response.put("replies", replies);
response.put("input", {"type": "select", "options": {"1", "2", "3"}});
```

**Key Finding:** There is NO separate `cards` field in any demo bot. All card-like displays use `replies` with `text` + `image`.

---

## 📋 **Handler-by-Handler Patterns**

### **Trigger Handler Pattern**

**Standard Structure:**
```deluge
response = Map();
response.put("action", "reply");
response.put("replies", {"Greeting message 1", "Greeting message 2"});
response.put("suggestions", {"Option 1", "Option 2", "Option 3"});
return response;
```

**Examples Found:**
- ✅ Simple string replies: `{"Hello!", "How can I help?"}`
- ✅ Map replies: `{{"text": "Hello!"}}`
- ✅ Multiple greeting lines supported

---

### **Message Handler Pattern**

**Standard Structure:**
```deluge
response = Map();
msg = message.get("text").toString().trim();

if(operation.equals("chat"))
{
    // First-time greeting
    response.put("action", "reply");
    response.put("replies", {"Welcome message"});
    response.put("suggestions", {...});
    return response;
}
else if(operation.equals("message"))
{
    // Handle user input
    if(msg.equalsIgnoreCase("Option 1"))
    {
        response.put("action", "context");
        response.put("context_id", "context_name");
        questions = Collection();
        // Add questions
        response.put("questions", questions);
    }
}
return response;
```

**Key Patterns:**
- ✅ Always check `operation` (chat vs message)
- ✅ Use `containsIgnoreCase()` for flexible matching
- ✅ Route to contexts with `action: "context"`
- ✅ Default fallback always provided

---

### **Context Handler Pattern**

**Standard Structure:**
```deluge
response = Map();
response.put("action", "context");
response.put("context_id", context_id);

if(context_id.equals("context_name"))
{
    // Extract answers
    ans = answers.get("field_name").get("text");
    
    // Handle logic
    if(ans.containsIgnoreCase("Value"))
    {
        // Next step: context, reply, forward, or end
        response.put("action", "reply"); // or "context", "forward", "end"
        response.put("replies", {...});
    }
}
return response;
```

**Key Patterns:**
- ✅ Safe answer extraction: `answers.get("field").get("text")`
- ✅ Use `containsIgnoreCase()` for matching
- ✅ Support nested contexts (context → context → reply)
- ✅ Always end with `return response;`

---

## 🎨 **Advanced Patterns**

### **1. Cards with Images (Ecommerce, Realtor, Education)**

**Pattern:**
```deluge
replies = Collection();
replies.insert({"text": "1. Product Name - Description", "image": "https://..."});
replies.insert({"text": "2. Product Name - Description", "image": "https://..."});
replies.insert({"text": "Select from given options"});
response.put("replies", replies);
response.put("input", {"type": "select", "options": {"1", "2", "3"}});
```

**NOT using:**
- ❌ No `cards` field
- ❌ No `type: "multiple-product"`
- ❌ No `elements` field

**Instead:**
- ✅ Use `replies` Collection
- ✅ Each reply is Map with `text` and optional `image`
- ✅ Add `input: {type: "select"}` for numbered options

---

### **2. API Calls (invokeurl pattern)**

**From our ContextHandler:**
```deluge
apiResult = invokeurl
[
    url:"https://api.example.com/endpoint"
    type:POST
    parameters:{"key":"value"}
];
```

**Pattern:**
- ✅ Always wrap in try-catch
- ✅ Check for null/empty results
- ✅ Provide fallback responses
- ✅ Parse JSON results safely

---

### **3. Input Types**

**Select Options:**
```deluge
"input": {
    "type": "select",
    "options": {"Option 1", "Option 2", "Option 3"}
}
```

**Date/Time Slots:**
```deluge
"input": {
    "type": "date-timeslots",
    "tz": true,
    "slots": {
        "30/08/2018": {"11:30", "15:00", "17:00"}
    },
    "skippable": true  // Optional
}
```

**Location:**
```deluge
"input": {
    "type": "location",
    "lat": "12.844037",
    "lng": "80.060411",
    "label": "Pick a location",
    "radius": "2 kms"
}
```

**Slider:**
```deluge
"input": {
    "type": "slider",
    "values": {"0", "10", "20", "30", "70"}
}
```

---

## 🔧 **Best Practices**

### **1. Error Handling**
```deluge
try
{
    // Code here
}
catch(err)
{
    info "Error: " + err;
    // Fallback response
    response.put("replies", {"Sorry, something went wrong."});
}
```

### **2. Null Safety**
```deluge
if(answers != null && answers.containsKey("field") && answers.get("field") != null)
{
    ans = answers.get("field").get("text");
}
```

### **3. Default Responses**
Always provide fallback:
```deluge
if(!hasReturned)
{
    response.put("action", "reply");
    response.put("replies", {"Please choose an option."});
    response.put("suggestions", mainOptions);
}
return response;
```

### **4. Multiple Reply Lines**
```deluge
response.put("replies", {
    "First message",
    "Second message",
    "Third message"
});
```

### **5. Suggestions Always Present**
Most bots include suggestions to guide users:
```deluge
mainOptions = Collection();
mainOptions.insert("Option 1");
mainOptions.insert("Option 2");
response.put("suggestions", mainOptions);
```

---

## 📊 **Comparison: Demo Bots vs Our Bot**

| Feature | Demo Bots | Our Bot | Status |
|---------|-----------|---------|--------|
| **Replies Format** | `replies` Collection | ✅ Using `replies` | ✅ Match |
| **Cards Display** | `replies` with `text` + `image` | ✅ Converted to `replies` | ✅ Match |
| **No Cards Field** | Never use `cards` | ✅ Removed `cards` | ✅ Match |
| **Suggestions** | Always include | ✅ Included | ✅ Match |
| **Error Handling** | Try-catch blocks | ✅ Implemented | ✅ Match |
| **Null Safety** | Check before access | ✅ Implemented | ✅ Match |
| **Default Fallback** | Always provided | ✅ Implemented | ✅ Match |
| **API Calls** | `invokeurl` with try-catch | ✅ Using `invokeurl` | ✅ Match |
| **Input Types** | select, date-timeslots, etc. | ✅ Using select | ✅ Match |

---

## 🎓 **Key Learnings**

1. **No `cards` field exists in any demo bot** - All use `replies` with Maps containing `text` + `image`
2. **Always use Collection for replies** - Either literal `{"..."}` or `Collection()` object
3. **Input with select for numbered options** - When displaying items with numbers
4. **Multiple reply lines** - Array of strings or Maps, all get displayed
5. **Suggestions guide users** - Almost all responses include suggestions
6. **Try-catch everywhere** - Especially for API calls and data extraction
7. **Null checks** - Always verify data exists before accessing
8. **Default fallback** - Always provide a response path

---

## ✅ **Our Bot Status**

All handlers have been updated to match demo bot patterns:

1. ✅ **TriggerHandler** - Matches demo patterns
2. ✅ **MessageHandler** - Matches demo patterns  
3. ✅ **FailureHandler** - Matches demo patterns
4. ✅ **ContextHandler** - Converted cards to replies format, matches demo patterns

**Ready for SalesIQ deployment! 🚀**

