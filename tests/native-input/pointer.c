#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "pointer.h"
static struct zwlr_virtual_pointer_manager_v1 *manager;
static void global(void*d,struct wl_registry*r,uint32_t n,const char*i,uint32_t v){if(!strcmp(i,"zwlr_virtual_pointer_manager_v1"))manager=wl_registry_bind(r,n,&zwlr_virtual_pointer_manager_v1_interface,1);}
static void removed(void*d,struct wl_registry*r,uint32_t n){}
static uint32_t now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000+t.tv_nsec/1000000;}
int main(){struct wl_display*d=wl_display_connect(NULL);if(!d)return 1;struct wl_registry*r=wl_display_get_registry(d);struct wl_registry_listener l={global,removed};wl_registry_add_listener(r,&l,NULL);wl_display_roundtrip(d);if(!manager)return 2;struct zwlr_virtual_pointer_v1*p=zwlr_virtual_pointer_manager_v1_create_virtual_pointer(manager,NULL);char line[128];int x,y;while(fgets(line,sizeof line,stdin)){if(sscanf(line,"move %d %d",&x,&y)==2)zwlr_virtual_pointer_v1_motion_absolute(p,now(),x,y,1920,1080);else if(!strncmp(line,"down",4))zwlr_virtual_pointer_v1_button(p,now(),272,1);else if(!strncmp(line,"up",2))zwlr_virtual_pointer_v1_button(p,now(),272,0);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);puts("ok");fflush(stdout);}zwlr_virtual_pointer_v1_button(p,now(),272,0);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);zwlr_virtual_pointer_v1_destroy(p);wl_display_disconnect(d);}
