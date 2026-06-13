/**
 * Send toast notifications (brief auto-expiring OS window element) to your user.
 * Can also be used with the Notification Web API.
 *
 * @module
 */
import { type PluginListener } from '@tauri-apps/api/core';
export type { PermissionState } from '@tauri-apps/api/core';
/**
 * Options to send a notification.
 *
 * @since 2.0.0
 */
interface Options {
    /**
     * The notification identifier to reference this object later. Must be a 32-bit integer.
     */
    id?: number;
    /**
     * Identifier of the {@link Channel} that deliveres this notification.
     *
     * If the channel does not exist, the notification won't fire.
     * Make sure the channel exists with {@link listChannels} and {@link createChannel}.
     */
    channelId?: string;
    /**
     * Notification title.
     */
    title: string;
    /**
     * Optional notification body.
     * */
    body?: string;
    /**
     * Schedule this notification to fire on a later time or a fixed interval.
     */
    schedule?: Schedule;
    /**
     * Multiline text.
     * Changes the notification style to big text.
     * Cannot be used with `inboxLines`.
     */
    largeBody?: string;
    /**
     * Detail text for the notification with `largeBody`, `inboxLines` or `groupSummary`.
     */
    summary?: string;
    /**
     * Defines an action type for this notification.
     */
    actionTypeId?: string;
    /**
     * Identifier used to group multiple notifications.
     *
     * https://developer.apple.com/documentation/usernotifications/unmutablenotificationcontent/1649872-threadidentifier
     */
    group?: string;
    /**
     * Instructs the system that this notification is the summary of a group on Android.
     */
    groupSummary?: boolean;
    /**
     * The sound resource name or file path for the notification.
     *
     * Platform specific behavior:
     * - On macOS: use system sounds (e.g., "Ping", "Blow") or sound files in the app bundle
     * - On Linux: use XDG theme sounds (e.g., "message-new-instant") or file paths
     * - On Windows: use file paths to sound files (.wav format)
     * - On Mobile: use resource names
     */
    sound?: string;
    /**
     * List of lines to add to the notification.
     * Changes the notification style to inbox.
     * Cannot be used with `largeBody`.
     *
     * Only supports up to 5 lines.
     */
    inboxLines?: string[];
    /**
     * Notification icon.
     *
     * On Android the icon must be placed in the app's `res/drawable` folder.
     */
    icon?: string;
    /**
     * Notification large icon (Android).
     *
     * The icon must be placed in the app's `res/drawable` folder.
     */
    largeIcon?: string;
    /**
     * Icon color on Android.
     */
    iconColor?: string;
    /**
     * Notification attachments.
     */
    attachments?: Attachment[];
    /**
     * Extra payload to store in the notification.
     */
    extra?: Record<string, unknown>;
    /**
     * If true, the notification cannot be dismissed by the user on Android.
     *
     * An application service must manage the dismissal of the notification.
     * It is typically used to indicate a background task that is pending (e.g. a file download)
     * or the user is engaged with (e.g. playing music).
     */
    ongoing?: boolean;
    /**
     * Automatically cancel the notification when the user clicks on it.
     */
    autoCancel?: boolean;
    /**
     * Changes the notification presentation to be silent on iOS (no badge, no sound, not listed).
     */
    silent?: boolean;
    /**
     * Notification visibility.
     */
    visibility?: Visibility;
    /**
     * Sets the number of items this notification represents on Android.
     */
    number?: number;
}
interface ScheduleInterval {
    year?: number;
    month?: number;
    day?: number;
    /**
     * 1 - Sunday
     * 2 - Monday
     * 3 - Tuesday
     * 4 - Wednesday
     * 5 - Thursday
     * 6 - Friday
     * 7 - Saturday
     */
    weekday?: number;
    hour?: number;
    minute?: number;
    second?: number;
}
declare enum ScheduleEvery {
    Year = "year",
    Month = "month",
    TwoWeeks = "twoWeeks",
    Week = "week",
    Day = "day",
    Hour = "hour",
    Minute = "minute",
    /**
     * Not supported on iOS.
     */
    Second = "second"
}
declare class Schedule {
    at: {
        date: Date;
        repeating: boolean;
        allowWhileIdle: boolean;
    } | undefined;
    interval: {
        interval: ScheduleInterval;
        allowWhileIdle: boolean;
    } | undefined;
    every: {
        interval: ScheduleEvery;
        count: number;
        allowWhileIdle: boolean;
    } | undefined;
    static at(date: Date, repeating?: boolean, allowWhileIdle?: boolean): Schedule;
    static interval(interval: ScheduleInterval, allowWhileIdle?: boolean): Schedule;
    static every(kind: ScheduleEvery, count: number, allowWhileIdle?: boolean): Schedule;
}
/**
 * Attachment of a notification.
 */
interface Attachment {
    /** Attachment identifier. */
    id: string;
    /** Attachment URL. Accepts the `asset` and `file` protocols. */
    url: string;
}
interface Action {
    id: string;
    title: string;
    requiresAuthentication?: boolean;
    foreground?: boolean;
    destructive?: boolean;
    input?: boolean;
    inputButtonTitle?: string;
    inputPlaceholder?: string;
}
interface ActionType {
    /**
     * The identifier of this action type
     */
    id: string;
    /**
     * The list of associated actions
     */
    actions: Action[];
    hiddenPreviewsBodyPlaceholder?: string;
    customDismissAction?: boolean;
    allowInCarPlay?: boolean;
    hiddenPreviewsShowTitle?: boolean;
    hiddenPreviewsShowSubtitle?: boolean;
}
interface PendingNotification {
    id: number;
    title?: string;
    body?: string;
    schedule: Schedule;
}
interface ActiveNotification {
    id: number;
    tag?: string;
    title?: string;
    body?: string;
    group?: string;
    groupSummary: boolean;
    data: Record<string, string>;
    extra: Record<string, unknown>;
    attachments: Attachment[];
    actionTypeId?: string;
    schedule?: Schedule;
    sound?: string;
}
declare enum Importance {
    None = 0,
    Min = 1,
    Low = 2,
    Default = 3,
    High = 4
}
declare enum Visibility {
    Secret = -1,
    Private = 0,
    Public = 1
}
interface Channel {
    id: string;
    name: string;
    description?: string;
    sound?: string;
    lights?: boolean;
    lightColor?: string;
    vibration?: boolean;
    importance?: Importance;
    visibility?: Visibility;
}
/**
 * Checks if the permission to send notifications is granted.
 * @example
 * ```typescript
 * import { isPermissionGranted } from '@tauri-apps/plugin-notification';
 * const permissionGranted = await isPermissionGranted();
 * ```
 *
 * @since 2.0.0
 */
declare function isPermissionGranted(): Promise<boolean>;
/**
 * Requests the permission to send notifications.
 * @example
 * ```typescript
 * import { isPermissionGranted, requestPermission } from '@tauri-apps/plugin-notification';
 * let permissionGranted = await isPermissionGranted();
 * if (!permissionGranted) {
 *   const permission = await requestPermission();
 *   permissionGranted = permission === 'granted';
 * }
 * ```
 *
 * @returns A promise resolving to whether the user granted the permission or not.
 *
 * @since 2.0.0
 */
declare function requestPermission(): Promise<NotificationPermission>;
/**
 * Sends a notification to the user.
 * @example
 * ```typescript
 * import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';
 * let permissionGranted = await isPermissionGranted();
 * if (!permissionGranted) {
 *   const permission = await requestPermission();
 *   permissionGranted = permission === 'granted';
 * }
 * if (permissionGranted) {
 *   sendNotification('Tauri is awesome!');
 *   sendNotification({ title: 'TAURI', body: 'Tauri is awesome!' });
 * }
 * ```
 *
 * @since 2.0.0
 */
declare function sendNotification(options: Options | string): void;
/**
 * Register actions that are performed when the user clicks on the notification.
 *
 * @example
 * ```typescript
 * import { registerActionTypes } from '@tauri-apps/plugin-notification';
 * await registerActionTypes([{
 *   id: 'tauri',
 *   actions: [{
 *     id: 'my-action',
 *     title: 'Settings'
 *   }]
 * }])
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function registerActionTypes(types: ActionType[]): Promise<void>;
/**
 * Retrieves the list of pending notifications.
 *
 * @example
 * ```typescript
 * import { pending } from '@tauri-apps/plugin-notification';
 * const pendingNotifications = await pending();
 * ```
 *
 * @returns A promise resolving to the list of pending notifications.
 *
 * @since 2.0.0
 */
declare function pending(): Promise<PendingNotification[]>;
/**
 * Cancels the pending notifications with the given list of identifiers.
 *
 * @example
 * ```typescript
 * import { cancel } from '@tauri-apps/plugin-notification';
 * await cancel([-34234, 23432, 4311]);
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function cancel(notifications: number[]): Promise<void>;
/**
 * Cancels all pending notifications.
 *
 * @example
 * ```typescript
 * import { cancelAll } from '@tauri-apps/plugin-notification';
 * await cancelAll();
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function cancelAll(): Promise<void>;
/**
 * Retrieves the list of active notifications.
 *
 * @example
 * ```typescript
 * import { active } from '@tauri-apps/plugin-notification';
 * const activeNotifications = await active();
 * ```
 *
 * @returns A promise resolving to the list of active notifications.
 *
 * @since 2.0.0
 */
declare function active(): Promise<ActiveNotification[]>;
/**
 * Removes the active notifications with the given list of identifiers.
 *
 * @example
 * ```typescript
 * import { cancel } from '@tauri-apps/plugin-notification';
 * await cancel([-34234, 23432, 4311])
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function removeActive(notifications: Array<{
    id: number;
    tag?: string;
}>): Promise<void>;
/**
 * Removes all active notifications.
 *
 * @example
 * ```typescript
 * import { removeAllActive } from '@tauri-apps/plugin-notification';
 * await removeAllActive()
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function removeAllActive(): Promise<void>;
/**
 * Creates a notification channel.
 *
 * @example
 * ```typescript
 * import { createChannel, Importance, Visibility } from '@tauri-apps/plugin-notification';
 * await createChannel({
 *   id: 'new-messages',
 *   name: 'New Messages',
 *   lights: true,
 *   vibration: true,
 *   importance: Importance.Default,
 *   visibility: Visibility.Private
 * });
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function createChannel(channel: Channel): Promise<void>;
/**
 * Removes the channel with the given identifier.
 *
 * @example
 * ```typescript
 * import { removeChannel } from '@tauri-apps/plugin-notification';
 * await removeChannel();
 * ```
 *
 * @returns A promise indicating the success or failure of the operation.
 *
 * @since 2.0.0
 */
declare function removeChannel(id: string): Promise<void>;
/**
 * Retrieves the list of notification channels.
 *
 * @example
 * ```typescript
 * import { channels } from '@tauri-apps/plugin-notification';
 * const notificationChannels = await channels();
 * ```
 *
 * @returns A promise resolving to the list of notification channels.
 *
 * @since 2.0.0
 */
declare function channels(): Promise<Channel[]>;
declare function onNotificationReceived(cb: (notification: Options) => void): Promise<PluginListener>;
declare function onAction(cb: (notification: Options) => void): Promise<PluginListener>;
export type { Attachment, Options, Action, ActionType, PendingNotification, ActiveNotification, Channel, ScheduleInterval };
export { Importance, Visibility, sendNotification, requestPermission, isPermissionGranted, registerActionTypes, pending, cancel, cancelAll, active, removeActive, removeAllActive, createChannel, removeChannel, channels, onNotificationReceived, onAction, Schedule, ScheduleEvery };
