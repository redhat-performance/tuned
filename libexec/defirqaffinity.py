#!/usr/bin/python

# Helper script for realtime profiles provided by RT

import os
import sys

irqpath = "/proc/irq/"

def bitmasklist(line):
	fields = line.strip().split(",")
	bitmasklist = []
	entry = 0
	for i in range(len(fields) - 1, -1, -1):
		mask = int(fields[i], 16)
		while mask != 0:
			if mask & 1:
				bitmasklist.append(entry)
			mask >>= 1
			entry += 1
	return bitmasklist

def get_cpumask(mask):
	groups = []
	comma = 0
	while mask:
		cpumaskstr = ''
		m = mask & 0xffffffff
		cpumaskstr += ('%x' % m)
		if comma:
			cpumaskstr += ','
		comma = 1
		mask >>= 32
		groups.append(cpumaskstr)
	string = ''
	for i in reversed(groups):
		string += i
	return string

def parse_def_affinity(fname):
	if os.getuid() != 0:
		return
	try:
		with open(fname, 'r') as f:
			line = f.readline()
		return bitmasklist(line)
	except IOError:
		return [ 0 ]

def verify(shouldbemask):
	inplacemask = 0
	fname = irqpath + "default_smp_affinity";
	cpulist = parse_def_affinity(fname)
	for i in cpulist:
		inplacemask = inplacemask | 1 << i;
	if (inplacemask & ~shouldbemask):
		sys.stderr.write("verify: failed: irqaffinity (%s) inplacemask=%x shouldbemask=%x\n" % (fname, inplacemask, shouldbemask))
		sys.exit(1)

	# now verify each /proc/irq/$num/smp_affinity
	interruptdirs = [ f for f in os.listdir(irqpath) if os.path.isdir(os.path.join(irqpath,f)) ]
	# IRQ 2 - cascaded signals from IRQs 8-15 (any devices configured to use IRQ 2 will actually be using IRQ 9)
	try:
		interruptdirs.remove("2")
	except ValueError:
		pass
	# IRQ 0 - system timer (cannot be changed)
	try:
		interruptdirs.remove("0")
	except ValueError:
		pass
	for i in interruptdirs:
		inplacemask = 0
		fname = irqpath + i + "/smp_affinity"
		cpulist = parse_def_affinity(fname)
		for i in cpulist:
			inplacemask = inplacemask | 1 << i;
		if (inplacemask & ~shouldbemask):
			sys.stderr.write("verify: failed: irqaffinity (%s) inplacemask=%x shouldbemask=%x\n" % (fname, inplacemask, shouldbemask))
			sys.exit(1)

	sys.exit(0)



# adjust default_smp_affinity
cpulist = parse_def_affinity(irqpath + "default_smp_affinity")
mask = 0
for i in cpulist:
	mask = mask | 1 << i;

if len(sys.argv) < 3 or len(str(sys.argv[2])) == 0:
	sys.stderr.write("%s: invalid arguments\n" % os.path.basename(sys.argv[0]))
	sys.exit(1)

line = sys.argv[2]
fields = line.strip().split(",")

for i in fields:
	if sys.argv[1] == "add":
		mask = mask | 1 << int(i);
	elif sys.argv[1] == "remove" or sys.argv[1] == "verify":
		mask = mask & ~(1 << int(i));
		
if sys.argv[1] == "verify":
	verify(mask)

string = get_cpumask(mask)

fo = open(irqpath + "default_smp_affinity", "wb")
fo.write(string)
fo.close()

# now adjust each /proc/irq/$num/smp_affinity

interruptdirs = [ f for f in os.listdir(irqpath) if os.path.isdir(os.path.join(irqpath,f)) ]

# IRQ 2 - cascaded signals from IRQs 8-15 (any devices configured to use IRQ 2 will actually be using IRQ 9)
try:
	interruptdirs.remove("2")
except ValueError:
	pass
# IRQ 0 - system timer (cannot be changed)
try:
	interruptdirs.remove("0")
except ValueError:
	pass

ret = 0
for i in interruptdirs:
	fname = irqpath + i + "/smp_affinity"
	cpulist = parse_def_affinity(fname)
	mask = 0
	for j in cpulist:
		mask = mask | 1 << j;
	for j in fields:
		if sys.argv[1] == "add":
			mask = mask | 1 << int(j);
		elif sys.argv[1] == "remove":
			mask = mask & ~(1 << int(j));
	string = get_cpumask(mask)
	try:
		fo = open(fname, "wb")
		fo.write(string)
		fo.close()
	except IOError as e:
		sys.stderr.write('Failed to set smp_affinity for IRQ %s: %s\n' % (str(i), str(e)))
		ret = 1
sys.exit(ret)
