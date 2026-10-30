// license:BSD-3-Clause
// @category Dana
// Read-only original-UK1.5 USB call graph and hardware wiring audit.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;
public class DanaISP1161FullAudit extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs();
  Memory memory=currentProgram.getMemory();
  if(memory.getBlock(toAddr(0xfffff000L))==null){
   MemoryBlock mmio=memory.createUninitializedBlock("USB_AUDIT_VZ_MMIO",toAddr(0xfffff000L),4096,false);
   mmio.setRead(true);mmio.setWrite(true);mmio.setVolatile(true);
  }
  if(memory.getBlock(toAddr(0x1f000000L))==null){
   MemoryBlock mmio=memory.createUninitializedBlock("USB_AUDIT_ISP1161",toAddr(0x1f000000L),8,false);
   mmio.setRead(true);mmio.setWrite(true);mmio.setVolatile(true);
  }
  try(PrintWriter out=new PrintWriter(new FileWriter(args[0]))){
   out.println("Original UK1.5 USB instruction/call audit; "+currentProgram.getLanguageID());
   // Validated entry points and their direct callees, never arbitrary constant hits.
   LinkedHashSet<Long> entries=new LinkedHashSet<Long>();
   for(long e:new long[]{0x1000305aL,0x10081732L,0x10301a6cL,0x10301aa8L,0x10301ac4L})entries.add(e);
   for(int i=1;i<args.length;i++)entries.add(Long.parseUnsignedLong(args[i],16));
   // Candidate USB routines have standard LINK entries. Their disassembly and
   // decompile are recorded explicitly, not silently treated as proven callers.
   if(args.length==1)for(long[] range:new long[][]{{0x10081680L,0x10081e00L},{0x10300000L,0x10302400L},{0x102ddd00L,0x102de300L}}){
    for(long a=range[0];a<range[1];a+=2)
     if(memory.getShort(toAddr(a))==(short)0x4e56)entries.add(a);
   }
   DecompInterface decomp=new DecompInterface();decomp.openProgram(currentProgram);
   for(long e:entries){
    Address start=toAddr(e);
    try{disassemble(start); for(int pass=0;pass<4;pass++){InstructionIterator fixes=currentProgram.getListing().getInstructions(start,true);int budget=0;while(fixes.hasNext()&&budget++<1200){Instruction x=fixes.next();if(x.getAddress().subtract(start)>0x1800)break;if(x.getMnemonicString().equalsIgnoreCase("trap")){x.setFallThrough(x.getMaxAddress().add(3));disassemble(x.getMaxAddress().add(3));}}} if(getFunctionAt(start)==null)createFunction(start,null);}catch(Exception ex){out.println("DECODE "+start+" "+ex);}
    Function function=getFunctionAt(start);
    out.printf("\nFUNCTION %08X %s\n",e,function);
    if(function==null)continue;
    out.println("CALLERS");
    for(ghidra.program.model.symbol.Reference ref:getReferencesTo(start))out.println(ref.getFromAddress()+" "+ref.getReferenceType());
    InstructionIterator it=currentProgram.getListing().getInstructions(function.getBody(),true);
    int count=0;
    while(it.hasNext()&&count++<1600){
     Instruction ins=it.next();
     out.println(ins.getAddress()+" "+ins);
     // Expose embedded Palm function names following RTS without decoding them.
     if(ins.getMnemonicString().equalsIgnoreCase("rts")){
      StringBuilder name=new StringBuilder();
      for(int j=0;j<64;j++){int b=memory.getByte(ins.getMaxAddress().add(1+j))&255;if(b>=32&&b<127)name.append((char)b);else name.append('.');}
      out.println("TRAILER "+name);
     }
    }
    DecompileResults result=decomp.decompileFunction(function,20,monitor);
    if(result.decompileCompleted())out.println(result.getDecompiledFunction().getC());
    else out.println("DECOMPILE_FAILED "+result.getErrorMessage());
   }
   decomp.dispose();
  }
  println("DANA_ISP1161_FULL_AUDIT_DONE");
 }
}
