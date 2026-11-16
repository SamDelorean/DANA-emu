// license:BSD-3-Clause
// @category Dana
// Bounded transient NetIF resource analysis in the existing readonly UK1.5 project.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
public class DanaH6NetifAudit extends GhidraScript {
 public void run() throws Exception {
  String[] a=getScriptArgs();byte[] prc=Files.readAllBytes(Paths.get(a[0]));int start=190,length=20946;
  Address base=toAddr(0x20000000L);Memory mem=currentProgram.getMemory();
  MemoryBlock block=mem.createInitializedBlock("H6_TRANSIENT_PRIVATE_NETIF",base,new ByteArrayInputStream(Arrays.copyOfRange(prc,start,start+length)),length,monitor,false);block.setExecute(true);block.setRead(true);
  Set<Long> entries=new TreeSet<Long>();entries.add(0L);entries.add(0xe4L);
  // Compiler LINK prologues are candidates, not independent proof of an API.
  for(int i=0;i<length-4;i+=2)if(prc[start+i]==0x4e && (prc[start+i+1]&255)==0x56)entries.add((long)i);
  for(long off:entries)try{disassemble(base.add(off));}catch(Exception ex){}
  for(int pass=0;pass<3;pass++) {
   InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(base,base.add(length-1)),true);
   while(it.hasNext()) {
    Instruction ins=it.next();
    if(ins.getMnemonicString().equalsIgnoreCase("trap"))try{ins.setFallThrough(ins.getMaxAddress().add(3));disassemble(ins.getMaxAddress().add(3));}catch(Exception ex){}
    for(Address t:ins.getFlows())if(t.compareTo(base)>=0 && t.compareTo(base.add(length))<0 && (ins.getFlowType().isCall() || ins.getMnemonicString().equalsIgnoreCase("bra")))entries.add(t.subtract(base));
   }
   for(long off:entries)try{disassemble(base.add(off));if(getFunctionAt(base.add(off))==null)createFunction(base.add(off),null);}catch(Exception ex){}
  }
  DecompInterface dc=new DecompInterface();dc.openProgram(currentProgram);
  try(PrintWriter out=new PrintWriter(new FileWriter(a[1]))) {
   out.println("READONLY TRANSIENT NetIF, resource neti/0 file+190, analysis base=20000000; "+currentProgram.getLanguageID());
   for(long off:entries) {
    Function fn=getFunctionAt(base.add(off));if(fn==null)continue;
    out.printf("\nFUNCTION resource+%04X file+%04X %s\n",off,off+start,fn);
    for(Reference ref:getReferencesTo(fn.getEntryPoint()))out.println("CALLER "+ref.getFromAddress()+" "+ref.getReferenceType());
    InstructionIterator it=currentProgram.getListing().getInstructions(fn.getBody(),true);int budget=0;
    while(it.hasNext()&&budget++<1800){Instruction ins=it.next();out.println(ins.getAddress()+" "+ins);}
    DecompileResults r=dc.decompileFunction(fn,15,monitor);if(r.decompileCompleted())out.println(r.getDecompiledFunction().getC());
   }
   out.println("\nROM NAMED FUNCTIONS");
   FunctionIterator it=currentProgram.getFunctionManager().getFunctions(true);
   while(it.hasNext()){Function f=it.next();if(f.getEntryPoint().getOffset()<0x20000000L && f.getName().toLowerCase().matches(".*(wifi|usbbus|sdio|wireless|usbpower).*"))out.println(f.getEntryPoint()+" "+f.getName());}
  }
  dc.dispose();println("H6_NETIF_READONLY_AUDIT_DONE functions="+entries.size());
 }
}
