<template>
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="app-icon">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="feather feather-mail"
                >
                    <path
                        d="M3 18v-12c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2h-14c-1.1 0-2-.9-2-2z"
                    />
                    <polyline points="3 6 12 13 21 6" />
                </svg>
            </div>
            <h2 class="sidebar-title">Control Panel</h2>
        </div>
        <ul class="sidebar-list">
            <li class="sidebar-list-item">
                <a href="#" class="sidebar-link active">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="feather feather-inbox"
                    >
                        <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
                        <path
                            d="M1 5.99988L7 12L1 18.0001"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        />
                        <path
                            d="M17 6H9H7H6"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        />
                    </svg>
                    Inbox
                </a>
            </li>
            <li class="sidebar-list-item">
                <a href="#" class="sidebar-link">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="feather feather-star"
                    >
                        <polygon
                            points="12 2 15.09 8.34 22 9.82 17 14 18.18 20.99 12 17.16 5.82 20.99 7 14 2 9.82 8.91 8.34 12 2"
                        />
                    </svg>
                    Starred
                </a>
            </li>
            <li class="sidebar-list-item">
                <a href="#" class="sidebar-link">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="feather feather-send"
                    >
                        <line x1="22" y1="2" x2="11" y2="13" />
                        <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                    Sent
                </a>
            </li>
            <li class="sidebar-list-item">
                <a href="#" class="sidebar-link">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="feather feather-file"
                    >
                        <path
                            d="M14 3v4a1 1 0 0 0 1 1h4M7 20H3a2 2 0 0 1-2-2V4c0-1.1.9-2 2-2h10l6 6v10a2 2 0 0 1-2 2h-4l-6-6z"
                        />
                    </svg>
                    Drafts
                </a>
            </li>
            <li class="sidebar-list-item">
                <a href="#" class="sidebar-link">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="feather feather-trash"
                    >
                        <polyline points="3 6 5 6 21 6" />
                        <path
                            d="M17 6L17 10C17 10.5304 16.7893 11.0391 16.4142 11.4142C16.0391 11.7893 15.5304 12 15 12H9C8.46957 12 7.96086 11.7893 7.58579 11.4142C7.21071 11.0391 7 10.5304 7 10L7 6M19 6L5 6M10 11L8 19H16L14 11H10Z"
                        />
                    </svg>
                    Trash
                </a>
            </li>
        </ul>
        <div class="account-info">
            <div class="account-info-picture">
                <img
                    src="https://via.placeholder.com/32"
                    alt="Profile Picture"
                />
            </div>
            <div class="account-info-name">John Doe</div>
            <button class="account-info-more">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="feather feather-chevron-down"
                >
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </button>
        </div>
    </div>
</template>

<script>
export default {
    name: 'ControlPanel',
}
</script>

<style scoped>
.sidebar {
    flex-basis: 200px;
    max-width: 200px;
    flex-shrink: 0;
    background-color: var(--sidebar);
    display: flex;
    flex-direction: column;
}

.sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
}

.sidebar-title {
    color: var(--sidebar-main-color);
    font-size: 18px;
    margin: 0;
}

.sidebar-list {
    list-style-type: none;
    padding: 0;
}

.sidebar-list-item {
    position: relative;
    margin-bottom: 4px;
}

.sidebar-link {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 10px 16px;
    color: var(--sidebar-link);
    text-decoration: none;
    font-size: 14px;
    line-height: 24px;
}

.sidebar-link.active {
    background-color: var(--sidebar-active-link);
}

.sidebar-link:hover {
    background-color: var(--sidebar-hover-link);
}

.app-icon {
    color: var(--sidebar-main-color);
}

.app-icon svg {
    width: 24px;
    height: 24px;
}

.account-info {
    display: flex;
    align-items: center;
    padding: 16px;
    margin-top: auto;
}

.account-info-picture {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
}

.account-info-picture img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.account-info-name {
    font-size: 14px;
    color: var(--sidebar-main-color);
    margin: 0 8px;
    overflow: hidden;
    max-width: 100%;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.account-info-more {
    color: var(--sidebar-main-color);
    padding: 0;
    border: none;
    background-color: transparent;
    margin-left: auto;
}
</style>
