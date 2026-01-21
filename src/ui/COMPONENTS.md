# UI Components Reference

**References:**
- UX Behavior (#12)
- Copy Rules (#13)
- UI Domain Adapter Layer (latest)

## Component Hierarchy

```
App
├── StatusIndicator
├── ConversationList
└── MessageList
    └── MessageRow (for each message)
```

## Component Props

### StatusIndicator
```typescript
interface StatusIndicatorProps {
  status: "Active Messaging" | "Messaging Disabled";
  isReadOnly: boolean;
}
```

### ConversationList
```typescript
interface ConversationListProps {
  conversations: ConversationViewModel[];
  onSelectConversation?: (conversationId: string) => void;
  isReadOnly: boolean;
}
```

### MessageList
```typescript
interface MessageListProps {
  messages: MessageViewModel[];
  conversationId: string;
  isReadOnly: boolean;
}
```

### MessageRow
```typescript
interface MessageRowProps {
  message: MessageViewModel;
  isReadOnly: boolean;
}
```

### App
```typescript
interface AppProps {
  deviceState: DeviceStateViewModel;
  conversations: ConversationViewModel[];
  messagesByConversation: Record<string, MessageViewModel[]>;
}
```

## Visual States

### Message States
- **Delivered**: Normal display (text-gray-900)
- **Failed**: Explicitly distinguishable (border-l-4 border-gray-400, "(Failed)" label)
- **Expired**: Not rendered (filtered out automatically)

### Read-Only Mode
- **Active**: Normal opacity
- **Read-only**: Reduced opacity (opacity-75), "Read-only" label displayed

### Device Status
- **Active Messaging**: Standard text color (text-gray-900)
- **Messaging Disabled**: Neutral gray (text-gray-600), "(Read-only)" indicator

## Deterministic Rules Enforced

1. **Reverse Chronological Ordering**: Messages displayed newest first per Resolved Clarifications (#53)
2. **Expired Message Filtering**: Expired messages removed automatically per UX Behavior (#12), Section 3.4
3. **Failed Message Distinction**: Failed messages explicitly distinguishable per UX Behavior (#12), Section 3.6
4. **Read-Only Indicators**: Neutral enterprise mode visual enforcement per Resolved Clarifications (#38)
5. **Neutral Color Scheme**: No red/green/security color metaphors per UX Behavior (#12), Section 5
6. **No Sound/Animation**: No urgency cues per UX Behavior (#12), Section 2

## Styling Guidelines

- **Colors**: Neutral grays only (gray-50, gray-100, gray-200, gray-400, gray-500, gray-600, gray-700, gray-900)
- **Typography**: System fonts, standard sizes (text-sm, text-xs)
- **Spacing**: Consistent padding (px-4, py-3) and gaps (gap-2, gap-4)
- **Borders**: Subtle borders (border-gray-100, border-gray-200)
- **No Animations**: Static UI only
- **No Icons**: Text-only indicators
