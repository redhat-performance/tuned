/*
 * varcpuload: Simple tool to create reproducable artifical sustained load on
 *             a machine.
 *
 * Copyright (C) 2008-2012 Red Hat, Inc.
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
 * Usage: varcpuload [-t time] [-n numcpu] [LOAD | MINLOAD MAXLOAD INCREASE]
 * LOAD, MINLOAD and MAXLOAD need to be between 1 and 100.
 * 
 * To compile:
 *   gcc -Wall -Os varcpuload.c -o varcpuload -lpthread
 * 
 * To measure load:
 * 1st terminal:
 *   for i in `seq 1 2 100`; do ./varcpuload -t 55 -n `/usr/bin/getconf _NPROCESSORS_ONLN` $i; done
 * or better
 *   ./varcpuload -t 60 -n `/usr/bin/getconf _NPROCESSORS_ONLN` 1 100 2; done
 * 2nd terminal:
 *   rm -f results; for i in `seq 1 2 100`; do powertop -d -t 60 >> results; done
 *
 * make sure the machine is otherwise idle, so start the machine initlevel 3 or even 1
 * and stop every unecessary service.
 * 
*/

#include <getopt.h>
#include <sys/time.h>
#include <pthread.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <ctype.h>

#define handle_error_en(en, msg) \
	do { errno = en; perror(msg); exit(EXIT_FAILURE); } while (0)

#define handle_error(msg) \
	do { perror(msg); exit(EXIT_FAILURE); } while (0)

#define ARRSIZE	512

int sleeptime = 0;
int duration  = 60;
int load      = 100;

void usage() {
	fprintf(stderr, "Usage: varload [-t time] [-n numcpu] [LOAD | MINLOAD MAXLOAD INCREASE]\n");
	fprintf(stderr, "LOAD, MINLOAD and MAXLOAD need to be between 1 and 100.\n");
}

int worker(void) {
	int i, j;
	float array[ARRSIZE][ARRSIZE];

	for (i = 0; i < ARRSIZE; i++) {
		for (j = 0; j < ARRSIZE; j++) {
			array[i][j] = (float)(i + j) / (float)(i + 1);
		}
	}

	return (int)array[1][1];
}

int timeDiff(struct timeval *tv1, struct timeval *tv2) {
	return (tv2->tv_sec - tv1->tv_sec) * 1000000 + tv2->tv_usec - tv1->tv_usec;
}

int getWorkerTime() {
	int cnt, i;
	struct timeval tv1, tv2;
	cnt = 0;
	gettimeofday(&tv1, NULL);
	gettimeofday(&tv2, NULL);
	// Warmup of 1 sec
	while (1000000 > timeDiff(&tv1, &tv2)) {
		i = worker();
		usleep(1);
		gettimeofday(&tv2, NULL);
	}
	gettimeofday(&tv1, NULL);
	gettimeofday(&tv2, NULL);
	// Meassure for 4 sec
	while (4*1000000 > timeDiff(&tv1, &tv2)) {
		i = worker();
		usleep(0);
		gettimeofday(&tv2, NULL);
		cnt++;
	}
	return timeDiff(&tv1, &tv2)/cnt;
}

static void * runWorker(void *arg) {
	int i;
	struct timeval tv1, tv2;
	gettimeofday(&tv1, NULL);
	gettimeofday(&tv2, NULL);
	while (duration > timeDiff(&tv1, &tv2)) {
		i = worker();
		usleep(sleeptime);
		gettimeofday(&tv2, NULL);
	}
	return NULL;
}

int main(int argc, char *argv[]) {
	int wtime, numcpu, opt, s, i;
	int minload, maxload, loadinc;
	pthread_attr_t attr;
	pthread_t *tid;
	void *res;

	numcpu = 1;

	while ((opt = getopt(argc, argv, "t:n:")) != -1) {
		switch (opt) {
		case 't':
			duration = atoi(optarg);
			break;
		case 'n':
			numcpu = atoi(optarg);
			break;
		default: /* '?' */
			usage();
			exit(EXIT_FAILURE);
		}
	}

	loadinc = 1;
	switch (argc - optind) {
	case 0:
		minload = 100;
		maxload = 100;
		break;
	case 1:
		minload = atoi(argv[optind]);
		maxload = minload;
		break;
	case 3:
		minload = atoi(argv[optind]);
		maxload = atoi(argv[optind + 1]);
		loadinc = atoi(argv[optind + 2]);
		break;
	default: /* '?' */
		usage();
		exit(EXIT_FAILURE);
	}

	if (minload < 1 || maxload < 1 || minload > 100 || maxload > 100) {
		usage();
		exit(EXIT_FAILURE);
	}

	wtime = getWorkerTime();
	duration *= 1000000;

	for (load = minload; load <= maxload; load += loadinc) {
		sleeptime = wtime * 100 / load - wtime;

		printf("Starting %d sec run with\n", duration / 1000000);
		printf("Load: %d\n", load);
		printf("Worker time: %d\n", wtime);
		printf("Sleep time: %d\n", sleeptime);
		printf("Nr. of CPUs to run on: %d\n", numcpu);

		s = pthread_attr_init(&attr);
		if (s != 0)
			handle_error_en(s, "pthread_attr_init");

		tid = malloc(sizeof(pthread_t) * numcpu);
		if (tid == NULL)
			handle_error("malloc");

		for (i = 0; i<numcpu; i++) {
			s = pthread_create(&tid[i], &attr, &runWorker, NULL);
			if (s != 0)
				handle_error_en(s, "pthread_create");
		}

		s = pthread_attr_destroy(&attr);
		if (s != 0)
			handle_error_en(s, "pthread_attr_destroy");

		for (i = 0; i < numcpu; i++) {
			s = pthread_join(tid[i], &res);
			if (s != 0)
				handle_error_en(s, "pthread_join");
		}

		free(tid);
	}
	exit(EXIT_SUCCESS);
}
