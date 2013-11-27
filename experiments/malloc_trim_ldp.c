/*
 * malloc_trim_ldp: A ld-preload library that can be used to potentially
 *                  save memory (especially for long running larger apps).
 *
 * Copyright (C) 2008-2013 Red Hat, Inc.
 * Authors: Phil Knirsch
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * To compile:
 *   gcc -Wall -fPIC -shared -lpthread -o malloc_trim_ldp.o malloc_trim_ldp.c
 *
 * To install:
 *   For a single app:
 *     LD_PRELOAD=./malloc_trim_ldp.o application
 *
 *   Systemwide:
 *     cp malloc_trim_ldp.o /lib
 *     echo "/lib/malloc_trim_ldp.o" >> /etc/ld.so.preload
 *
 * How it works:
 *   This ld-preload library simply redirects the glibc free() call to a new
 *   one that simply has a static counter and every 10.000 free() calls will
 *   call malloc_trim(0) which goes through the heap of an application and
 *   basically releases pages that aren't in use anymore using madvise().
 *
 */

#include <malloc.h>
#include <stdlib.h>
#include <stdio.h>
#include <limits.h>
#include <sys/types.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <pthread.h>

static pthread_mutex_t mymutex = PTHREAD_MUTEX_INITIALIZER;
static int malloc_trim_count=0;

static void mymalloc_install (void);
static void mymalloc_uninstall (void);

static void (*old_free_hook) (void *, const void *);

static void myfree(void *ptr, const void *caller)
{
	pthread_mutex_lock(&mymutex);
	malloc_trim_count++;
	if(malloc_trim_count%10000 == 0) {
		malloc_trim(0);
	}

	mymalloc_uninstall();
	free(ptr);
	mymalloc_install();
	pthread_mutex_unlock(&mymutex);
}

static void mymalloc_install (void)
{
  old_free_hook = __free_hook;
  __free_hook = myfree;
}

static void mymalloc_uninstall (void)
{
  __free_hook = old_free_hook;
}

void (*__malloc_initialize_hook) (void) = mymalloc_install;
