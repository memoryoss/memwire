import * as React from "react"
import { Link, useLocation } from "react-router-dom"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import { TeamSwitcher } from "@/components/team-switcher"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { navGroups, settingsNav } from "@/lib/nav-data"

const user = {
  name: "Harshal More",
  email: "harshal@memwire.dev",
  avatar: "/avatars/user.jpg",
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { pathname } = useLocation()
  const settingsActive = pathname === settingsNav.url
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher />
      </SidebarHeader>
      <SidebarContent>
        {navGroups.map((group) => (
          <NavMain key={group.label} group={group} />
        ))}
      </SidebarContent>
      <SidebarFooter>
        <SidebarSeparator />
        <SidebarGroup className="py-1">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                tooltip={settingsNav.title}
                isActive={settingsActive}
              >
                <Link to={settingsNav.url}>
                  {settingsNav.icon}
                  <span>{settingsNav.title}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>
        <NavUser user={user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
